import json
import math
import sys

from django.core.management.base import BaseCommand
from api.enums import Difficulty

from api.models import (
    Experience,
)

allowed_geotag_symbols = r'/ -0123456789,.°NESW\'"'

class Command(BaseCommand):

    def extract_description(self, data: dict) -> str:
        description = data['description']
        if data['description'] is None or data['description'].strip() != '':
            description = '<No Description>'
        return description[:1000]

    def extract_name(self, data: dict) -> str:
        segment1: str = data['action']
        segment2: str = data['experience']
        if segment1 is not None and segment1.strip() == '':
            segment1 = None
        if segment2 is not None and segment2.strip() == '':
            segment2 = None
        if segment1 is None and segment2 is None:
            return '<No Name>'
        name = ''
        if segment1 is not None and segment2 is not None:
            name = f'{segment1} {segment2}'
        elif segment2 is not None:
            name = segment2
        return name[:100]

    def extract_directions(self, data:dict) -> str:
        directions = data['other_address_note']
        if directions is None:
            return None
        return directions[:1000]

    def extract_difficulty(self, data:dict) -> str:
        difficulty = data['difficult_level']
        if difficulty is None:
            return None
        if difficulty == 'easy':
            return Difficulty.EASY
        if difficulty == 'moderate':
            return Difficulty.MODERATE
        elif difficulty == 'hard':
            return Difficulty.HARD
        return None

    def extract_geotag(self, data: dict) -> str:
        geotag: str = data['geo_tag']
        if geotag is None:
            geotag = data['geo_link']
        if geotag is None or geotag.strip() == '':
            return None

        # Strip out all the weird special characters from the original data
        cleaned_geotag = ''
        for char in geotag:
            if char == '″':
                cleaned_geotag += '"'
                continue
            if char == '′':
                cleaned_geotag += "'"
                continue
            if char == ';':
                cleaned_geotag += ','
                continue
            if char in allowed_geotag_symbols:
                cleaned_geotag += char
        geotag = cleaned_geotag.strip()

        # Handle
        # 67°47′N 153°18′W / 67.78°N 153.30°W / 67.78; -153.30
        split_on_slash = geotag.split('/')
        for i in range(0, len(split_on_slash)):
            split_on_slash[i] = split_on_slash[i].strip()
        if len(split_on_slash) == 3:
            value = split_on_slash[2].strip()
            split_on_semicolon = value.split(';')
            if len(split_on_semicolon) == 2:
                return ', '.join(split_on_semicolon)
            else:
                return value
        return geotag


    def handle(self, *args, **options):
        data_dir = 'api/management/commands/old_db_seed_data'
        information: list[dict] = []

        print('Pulling data for: information')
        with open(f'{data_dir}/information.json', 'r') as file:
            information = json.loads(file.read())['information']

        print(f'  Records:         {len(information)}')
        _created = 0
        _already_existed = 0
        _error_skipped = 0
        try:
            for i, data in enumerate(information):
                description = self.extract_description(data)
                name = self.extract_name(data)
                experience, created = Experience.objects.get_or_create(
                    original_id=data['id'],
                    file_is_image=False,
                    name=name,
                    description=description)

                if created:
                    _created += 1
                else:
                    _already_existed += 1

                address = data['address']
                city = data['city']
                state = data['state']
                zip = data['zip_code']
                country = data['country']

                location = [
                    address,
                    city,
                    state,
                    zip,
                    country
                ]
                location = [l for l in location if bool(l)]
                experience.location = ', '.join(location)

                experience.directions = self.extract_directions(data)
                experience.difficulty = self.extract_difficulty(data)
                experience.geo_tag = self.extract_geotag(data)

                experience.save()

                progress = i / len(information)
                progress *= 1000
                progress = math.floor(progress)
                sys.stdout.write("  Progress: %s%%   \r" % (progress/10) )

        except Exception as e:
            _error_skipped += 1

        print('')
        print(f'  Created:         {_created}')
        print(f'  Already Existed: {_already_existed}')
        print(f'  Error Skipped:   {_error_skipped}')
