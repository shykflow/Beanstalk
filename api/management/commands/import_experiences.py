from typing import Any
from io import TextIOWrapper
import json
import math
import os
import sys
from apiclient import discovery
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandParser
from google.oauth2.service_account import Credentials

from api.utils.command_line_spinner import CommandLineSpinner
from api.models import (
    Experience,
    ExperienceCostRating,
    User,
)
from api.management.commands.helpers.experience_google_sheet import (
    Merge,
    Row,
)

ENV = os.environ

class Command(BaseCommand):
    dryrun: bool = False
    search_categories: bool = True
    use_test_sheet: bool = False
    test_sheet_name = '(TEST)'
    user: User
    log_dir: str = os.path.join(settings.BASE_DIR, 'api', 'management', 'commands','logs')
    log_file_name: str = 'import_experiences.log'
    log_file: TextIOWrapper

    def can_import_sheet(self, sheet_title: str) -> bool:
        allowed: bool
        if Command.use_test_sheet:
            return sheet_title == Command.test_sheet_name

        allowed = sheet_title.upper().startswith('(VALIDATED)')
        if not allowed:
            self.log(f'  {sheet_title} {"(SKIPPED)" if allowed else ""}')
        return allowed


    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument('--dryrun', action='store_true', default=False)
        parser.add_argument('--search-categories', action='store_true', default=False)
        parser.add_argument('--use-test-sheet', action='store_true', default=False)


    def print_progress(self, on: int, outof: int):
        progress = on / outof
        progress *= 100
        progress = math.floor(progress)
        sys.stdout.write("Progress: %s%%   \r" % (progress))


    def get_sheet_service(self):
        creds_file_name = "google_sheets_crawler.json"
        creds_path = os.path.join(settings.BASE_DIR, creds_file_name)
        if not os.path.exists(creds_path):
            print('  Cannot import from sheet:')
            print(f'    {creds_path} does not exist.')
            exit(1)
        with open(creds_path) as creds_file:
            creds_dict = json.loads(creds_file.read())
            private_key = creds_dict.get('private_key', '')
            if private_key.strip() == '':
                print('  Cannot import from sheet:')
                print('    Bad credentials file')
                exit(1)
        credentials = Credentials.from_service_account_file(
            filename=creds_path,
            scopes=['https://www.googleapis.com/auth/spreadsheets'])
        service = discovery.build('sheets', 'v4', credentials=credentials)
        return service


    def prep_log_file(self):
        if not os.path.exists(Command.log_dir):
            os.mkdir(Command.log_dir)
        file_path = f'{Command.log_dir}/{Command.log_file_name}'
        if os.path.exists(file_path):
            os.remove(file_path)
        Command.log_file = open(file_path, 'a')


    def log(self, msg, print_msg=True):
        if print_msg:
            print(msg)
        Command.log_file.write(msg + '\n')


    def log_row_errors(self, row: Row):
        msg = f'  Error(s) on Row {row.row_number + 1} | {row.errors}'
        self.log(msg, print_msg=False)


    def create_beanstalk_user(self):
        sender_domain = settings.ANYMAIL['MAILGUN_SENDER_DOMAIN']
        user, created = User.objects.get_or_create(
            username='beanstalk',
            email=f'beanstalk@{sender_domain}')
        user.email_verified = True
        user.set_password('Test1234$')
        user.save()
        Command.user = user

    def log_dryrun(self):
        if Command.dryrun:
            self.log('=====================================')
            self.log('||            DRY RUN              ||')
            self.log('=====================================')

    def get_spreadsheet_metadata(self) -> Any:
        self.log(f'Getting metadata for Spread Sheet ID: {self.spreadsheet_id}')
        with CommandLineSpinner():
            metadata = self.sheet_service.spreadsheets() \
                .get(spreadsheetId=self.spreadsheet_id) \
                .execute()
            self.log('  Got Spread Sheet metadata')
        return metadata

    def get_sheets(self, spreadsheet_metadata) -> list:
        self.log('Getting child Sheets metadata from Spread Sheet metadata')
        _sheets = []
        with CommandLineSpinner():
            _sheets = spreadsheet_metadata.get('sheets')
            self.log('  Got child Sheets metadata')
        if _sheets is None:
            self.log('  Cannot read sheets metadata\n')
            exit(1)
        self.log('Found these sheets:')
        sheets = []
        for sheet_metadata in _sheets:
            sheet_title: str = sheet_metadata.get('properties', {}).get('title')
            if self.can_import_sheet(sheet_title):
                sheets.append(sheet_metadata)
        return sheets

    def parse_merges(self, merges: list) -> list:
        # The first row is the title bar, we don't care if there are merges there
        return [
            Merge(m)
            for m in merges
            if m['startRowIndex'] !=0 and m['endRowIndex'] != 1
        ]

    def build_sheet_range(self, sheet_title) -> str:
        cell_range = 'A1:AA'
        if ' ' in sheet_title:
            return f"'{sheet_title}'!{cell_range}"
        else:
            return f'{sheet_title}!{cell_range}'

    def get_data_in_sheet_range(self, range: str):
        self.log(f'  Getting tabular data')
        try:
            with CommandLineSpinner():
                return self.sheet_service.spreadsheets().values() \
                    .get(spreadsheetId=self.spreadsheet_id, range=range) \
                    .execute()
        except Exception as e:
            self.log(str(e))
            return None


    def handle_command_line_args(self, options: dict[str, Any]):
        Command.dryrun = options['dryrun']
        Command.search_categories = options['search_categories']
        Command.use_test_sheet = options['use_test_sheet']

    def handle(self, *args, **options):
        self.handle_command_line_args(options)
        self.spreadsheet_id = ENV.get('EXPERIENCES_GOOGLE_SHEET_ID')
        self.prep_log_file()
        self.sheet_service = self.get_sheet_service()
        self.log_dryrun()
        self.create_beanstalk_user()
        spreadsheet_metadata = self.get_spreadsheet_metadata()
        sheets = self.get_sheets(spreadsheet_metadata)
        for i, sheet_metadata in enumerate(sheets):
            self.log('------------------------------------------')
            properties = sheet_metadata['properties']
            sheet_id = properties['sheetId']
            sheet_title: str = properties['title'].strip()
            merges = self.parse_merges(sheet_metadata.get('merges', []))

            if sheet_id is None:
                self.log(f'  Could not get Sheet ID for sheet {i}')
                continue
            if sheet_title is None or sheet_title == '':
                self.log(f'  Sheet ID: {sheet_id} had no title')
                continue
            self.log(sheet_title)

            range = self.build_sheet_range(sheet_title)
            table_data = self.get_data_in_sheet_range(range)
            if table_data is None:
                continue

            data: list[list[str]] = table_data.get('values', [])
            self.log(f'  Found {len(data)} rows')
            len_rows = len(data)
            experiences: list[Experience] = []
            created: list[Row] = []
            row_data: list[str]
            for i, row_data in enumerate(data):
                if i == 0:
                    self.log('  Skipping the column names row')
                    continue
                row_merges = [m for m in merges if m.start_row_index == i]
                row = Row(
                    search_categories = Command.search_categories,
                    created_by=Command.user,
                    sheet_title=sheet_title,
                    row_number=i,
                    data_list=row_data,
                    merges=row_merges)
                if row.empty:
                    continue
                if bool(row.errors):
                    self.log_row_errors(row)
                    continue
                self.print_progress(i, len_rows)
                created.append(row)
                if not Command.dryrun:
                    experiences.append(row.experience)
                if len(experiences) % 100 == 0:
                    Experience.objects.bulk_create(experiences)
                    experiences = []
                self.print_progress(i, len_rows)
            self.print_progress(1, 1)
            print()
            if len(experiences) > 0:
                Experience.objects.bulk_create(experiences)
            self.log(f'  Experiences Created {len(created)}')

            ratings: list[ExperienceCostRating] = []
            for row in created:
                experience = row.experience
                if not experience.cost_needs_review and row.cost != None:
                    ratings.append(ExperienceCostRating(
                        experience=experience,
                        created_by=Command.user,
                        rating=row.cost
                    ))
            if not Command.dryrun:
                ExperienceCostRating.objects.bulk_create(ratings)
            self.log(f'  Cost Ratings Created: {len(ratings)}')

        self.log(f'Searches avoided: {Row.category_searches_avoided}')

        call_command('convert_geotag_to_lat_lng')

        Command.log_file.close()
