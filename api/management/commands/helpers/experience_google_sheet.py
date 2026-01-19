import json
import os
import re
import requests

from . import AXIS_DIRECTIONS, REGEX
from api.enums import (
    Difficulty,
    Publicity,
)
from api.models import (
    Experience,
    User,
)
from lf_service.models import Category
from lf_service.category import LifeFrameCategoryService

ENV = os.environ


DIFFICULTIES_DICT = {
    'EASY': ['1', '', 'EASY'],
    'MEDIUM': ['2', 'AVERAGE', 'MODERATE', 'MEDIUM'],
    'HARD': ['3', 'HARD', 'DIFFICULT'],
    'EXTREME': ['4', 'EXTREME'],
}


class Merge:
    def __init__(self, data: dict[str,int]):
        self.start_row_index = data['startRowIndex']
        self.end_row_index = data['endRowIndex']
        self.start_col_index = data['startColumnIndex']
        self.end_col_index = data['endColumnIndex']
    def __str__(self):
        start_row = str(self.start_row_index).ljust(5)
        end_row = str(self.end_row_index).ljust(5)
        start_col = str(self.start_col_index).ljust(2)
        end_col = str(self.end_col_index).ljust(2)
        s = f'Start Row {start_row} | '
        s += f'End Row {end_row} | '
        s += f'Start Col {start_col} | '
        s += f'End Col {end_col}'
        return s



class Row:
    category_searches_avoided = 0
    category_cache: dict[str, int] = {}
    category_service = LifeFrameCategoryService()

    def __init__(
            self,
            search_categories: bool,
            created_by: User,
            sheet_title: str,
            row_number:int,
            data_list:list[str],
            merges: list[Merge]):
        self.search_categories = search_categories
        self.created_by = created_by
        self.sheet_title: str = sheet_title
        self.row_number: int = row_number
        self.empty: bool = len(data_list) == 0
        self.errors: dict[str, str] = {}
        self.categories: list[int]
        self.requested_categories: list[str]

        self.data = self.build_data_dict(data_list, merges)
        self.notes: str = self.data['notes']
        self.title: str = self.data['title']
        if self.title is None or len(self.title.strip()) == 0:
            self.errors['Title'] = 'Title is blank'
        elif len(self.title) > 250:
            self.errors['Title'] = f'Max 250 characters, was {len(self.title)} long'

        category_ids, requested_categories = self.parse_categories(self.data['categories'])
        self.categories = category_ids
        self.requested_categories = requested_categories

        self.description: str = self.data['description']
        if self.description is not None and len(self.description) > 100000:
            self.errors['Description'] = f'Max 100000 characters, was {len(self.description)} long, ' +\
                'consider linking to a web site instead.'

        self.geo_tag = self.parse_geotag(self.data['geotag'])
        self.location = None
        if self.geo_tag is None:
            self.location: str = self.data['location']
            # Geotag didn't match any regexes but the raw geotag is not none
            if self.data['geotag'] is not None and self.location is None:
                self.location = self.data['geotag']
            # Location is too long, move to description
            elif self.location is not None and len(self.location) > 500:
                self.description += f'\n\n{self.location}'
                self.description = self.description[:100000]
                self.location = None

        directions: str = self.data['directions']
        if directions is not None and directions.strip() != '':
            if self.description is None:
                self.description = directions
            else:
                self.description += f'\n\n{directions}'
                self.description = self.description[:100000]
        self.timebase: str = self.data['timebase']
        self.difficulty = self.parse_difficulty(self.data['difficulty'])
        self.experience: Experience = None
        self.website: str = self.data['website']

        # Measurements
        self.elevation_gain: str = self.parse_measurement(
            value=self.data['elevation_gain'],
            error_key='Elevation Gain')
        self.length: str = self.parse_measurement(
            value=self.data['length'],
            error_key='Length')
        self.elevation: str = self.parse_measurement(
            value = self.data['elevation'],
            error_key='Elevation')
        if self.length or self.elevation or self.elevation_gain:
            values = [
                x
                for x in [
                    f'Length: {self.length}' if self.length else None,
                    f'Elevation: {self.elevation}' if self.elevation else None,
                    f'Elevation Gain: {self.elevation_gain}' if self.elevation_gain else None,
                ]
                if x is not None
            ]
            measurements = ''
            if len(values) > 0:
                measurements = '\n'.join(values)

            if self.description is None or self.description == '':
                self.description = measurements
            else:
                self.description += f"\n\n{measurements}"

        # Cost
        parsed_cost = self.parse_cost(self.data['cost'])
        self.cost: int = parsed_cost['value']
        self.cost_description: str = parsed_cost['description']
        self.cost_needs_review: bool = parsed_cost['needs_review']

        if not bool(self.errors):
            try:
                self.experience = self.to_experience()
            except Exception as e:
                self.errors['Unknown'] = 'Something went wrong when converting the row to a Experience'


    def build_data_dict(self, data_list: list[str], merges: list[Merge]) -> dict[str, any]:
        for i, value in enumerate(data_list):
            data_list[i] = value.strip()
        data = {
            'notes': self.value_at(data_list, merges, 0),
            'title': self.value_at(data_list, merges, 1),
            'description': self.value_at(data_list, merges, 17),
            'location': self.value_at(data_list, merges, 18),
            'geotag': self.value_at(data_list, merges, 19),
            'directions': self.value_at(data_list, merges, 20),
            'timebase': self.value_at(data_list, merges, 21),
            'cost': self.value_at(data_list, merges, 22),
            'difficulty': (self.value_at(data_list, merges, 23) or '').upper(),
            'elevation_gain': self.value_at(data_list, merges, 24),
            'length': self.value_at(data_list, merges, 25),
            'elevation': self.value_at(data_list, merges, 26),
            'website': self.value_at(data_list, merges, 27),
        }
        categories: list[str] = []
        for i in range(2, 17):
            category_name = self.value_at(data_list, merges, i)
            if category_name is None:
                continue
            categories.append(category_name.upper())
        data['categories'] = categories
        return data


    def value_at(self, data: list[str], merges: list[Merge], index: int) -> str|None:
        value = None
        contain_index_merges = [
            m
            for m in merges
            if index >= m.start_col_index and index < m.end_col_index
        ]
        if index >= len(data):
            return None
        if len(contain_index_merges) > 0:
            merge = contain_index_merges[0]
            if merge.start_col_index <= index < merge.end_col_index:
                if index == merge.start_col_index:
                    return data[index] or None
                return None
        value = data[index]
        return value or None

    def parse_measurement(self, value:str|None, error_key:str) -> str|None:
        """
        Attempts to make measurements similar for easier importing to the db.
        If no "measurement type" specified, will default to "ft".
        For instance:
        ```
            "2000"                => "2000 ft"
            "100ft"               => "100 ft"
            "1,000 ft"            => "1000 ft"
            "1000feet"            => "1000 ft"
            "1000 feet"           => "1000 ft"
            "1,001.5 KM"          => "1001.5 km"
            "1,001.25 kilometers" => "1001.25 km"
            "2m"                  => "2.0 m"
        ```
        """
        try:
            if value is None or value.strip() == '':
                return None
            value = ''.join(value.split())
            value = value.replace(',', '')
            value = value.lower()
            length: float = None
            unit: str = None
            # should pass 1000 and 1,000, default to ft because no measurement detected
            if value.replace('.', '').isdigit():
                length = float(value)
                unit = 'ft'
            elif value.endswith('feet'):
                length = float(value[:-4])
                unit = 'ft'
            elif value.endswith('ft'):
                length = float(value[:-2])
                unit = 'ft'
            elif value.endswith('km'):
                length = float(value[:-2])
                unit = 'km'
            elif value.endswith('kilometers'):
                length = float(value[:-10])
                unit = 'km'
            elif value.endswith('meters'):
                length = float(value[:-6])
                unit = 'm'
            elif value.endswith('m'):
                length = float(value[:-1])
                unit = 'm'
            elif value.endswith('mi'):
                length = float(value[:-2])
                unit = 'mi'
            else:
                raise Exception()
            if int(length) == length:
                length = int(length)
            return f'{length} {unit}'
        except:
            # self.errors[error_key] = f'Could not read, received {value}'
            return None


    def parse_geotag(self, geotag: str):
        if geotag is None:
            return None
        try:
            valid = re.match(REGEX['geo_lat_long'], geotag) or \
                    re.match(REGEX['geo_hour_min_sec'], geotag) or \
                    re.match(REGEX['geo_degree_quote'], geotag)
            if not valid:
                can_adapt = re.match(REGEX['geo_lat_long_can_adapt'], geotag)
                if can_adapt:
                    split = geotag.split()
                    split = [s for s in split if s not in AXIS_DIRECTIONS]
                    geotag = ''.join(split)
                else:
                    raise Exception
            return geotag
        except:
            # self.errors['Geo Tag'] = f'Could not recognize geotag, received "{geotag}"'
            return None


    def parse_cost(self, cost: str) -> dict[str, any]:
        """
        Determine if the cost field is blank, a $$$ amount, or 0 through 4
        """
        parsed = {
            'value': None,
            'description': None,
            'needs_review': False,
        }
        def try_parse_int(value: str) -> int|None:
            try:
                return int(value)
            except:
                return None
        try:
            if cost is None:
                return parsed
            if cost.upper() == 'FREE':
                parsed['value'] = 0
            if parsed['value'] is None:
                cost_int = try_parse_int(cost)
                if cost_int is not None and 0 <= cost_int <= 4:
                    parsed['value'] = cost_int
            if parsed['value'] is None:
                # 1 to 4 dollar signs
                dollars_match = re.match(REGEX['cost_dollars'], cost)
                if dollars_match:
                    parsed['value'] = len(cost)
            if parsed['value'] is None:
                raise Exception()
        except:
            parsed['value'] = None
            parsed['description'] = cost
            parsed['needs_review'] = True
        return parsed


    def parse_difficulty(self, difficulty: str) -> Difficulty:
        if difficulty is None:
            return None
        difficulty = difficulty.upper()
        if difficulty in DIFFICULTIES_DICT['EASY']:
            return Difficulty.EASY
        if difficulty in DIFFICULTIES_DICT['MEDIUM']:
            return Difficulty.MODERATE
        if difficulty in DIFFICULTIES_DICT['HARD']:
            return Difficulty.DIFFICULT
        if difficulty in DIFFICULTIES_DICT['EXTREME']:
            return Difficulty.EXTREME
        if difficulty == 'UNRATED OR AT YOUR RISK':
            return None
        self.errors['Difficulty'] = f'Unrecognized, found "{difficulty}"'
        return None


    def parse_categories(self, category_names: list[str]) -> tuple[list[int], list[str]]:
        """
        Returns a tuple, in the first position are the category ids of the categories
        found in LifeFrame, the second position is the unrecognized category names.
        """
        category_ids: list[int] = []
        not_matched_names: list[str] = []
        if self.search_categories:
            name: str
            for name in category_names:
                name_upper = name.upper()
                id = Row.category_cache.get(name_upper)
                if id is None:
                    # Not cached yet
                    try:
                        matches = Row.category_service.search(
                            phrase=name_upper,
                            threshold=0.90)
                    except requests.exceptions.ConnectionError as e:
                        print('Could not communicate with LifeFrame, is it running?')
                        exit(1)
                    if len(matches) > 0:
                        category: Category = matches[0]
                        id = category.id
                    else:
                        id = -1
                    Row.category_cache[name_upper] = id
                elif id == -1:
                    # Was previously not found
                    Row.category_searches_avoided += 1
                else:
                    # Was previously found and cached
                    Row.category_searches_avoided += 1
                if id == -1:
                    not_matched_names.append(name)
                else:
                    category_ids.append(id)
        return (category_ids, not_matched_names,)

    def to_experience(self):
        return Experience(
            created_by_id=self.created_by.pk,
            name=self.title,
            description=self.description,
            categories=self.categories,
            requested_categories=self.requested_categories,
            cost_description=self.cost_description,
            difficulty=self.difficulty,
            visibility=Publicity.PUBLIC,
            geo_tag=self.geo_tag,
            location=self.location,
            website=self.website,
            categories_need_manual_review=len(self.requested_categories) > 0,
            original_data=json.dumps(self.data, indent=4))
