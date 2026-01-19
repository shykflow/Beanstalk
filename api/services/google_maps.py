import colorama
import logging
import os
import requests
from urllib.parse import urlencode

logger = logging.getLogger('app')


class GoogleMapsException(Exception):
    def __init__(self, response: requests.Response=None, message="Something went wrong querying Google Maps"):
        self.response: requests.Response | None = response
        self.status_code: int | None = None
        if response is not None:
            self.status_code = response.status_code
        message = f'{message}\nStatus Code: {self.status_code}, {message}'
        super().__init__(message)


class GoogleMapsService:

    log_label = 'GoogleMapsService'

    def __init__(self):
        env = os.environ
        self.api_url = 'https://maps.googleapis.com/maps/api'
        self.geocoding_key = env.get('GEOCODING_GOOGLE_MAPS_KEY')
        self.places_key = env.get('PLACES_GOOGLE_MAPS_KEY')

    def _log(self, message: str):
        color = colorama.Fore.GREEN
        bright = colorama.Style.BRIGHT
        reset = colorama.Style.RESET_ALL
        logger.info(f"{bright}{color}{self.log_label}:{reset} {message}")

    def params_to_url_part(self, params: dict[str, str]) -> str:
        if not bool(params):
            return ''
        return '?' + urlencode(params)

    def autocomplete_place(self, search_term: str, token: str):
        """
        See https://developers.google.com/maps/documentation/places/web-service/autocomplete
        """
        query_params = {
            'input': search_term,
            'sessiontoken': token,
            'key': self.places_key
        }
        url = ''.join([
            self.api_url,
            '/place/autocomplete/json',
            self.params_to_url_part(query_params)
        ])
        self._log(f'GET {url}')
        response = requests.get(url)
        if not 200 <= response.status_code < 300:
            raise GoogleMapsException(response=response)
        data = response.json()
        # https://developers.google.com/maps/documentation/places/web-service/autocomplete#PlacesAutocompleteStatus
        if data['status'] == 'OK' or data['status'] == 'ZERO_RESULTS':
            return data
        raise GoogleMapsException(response=response)

    def place_details(self, place_id: str, token: str):
        """
        See https://developers.google.com/maps/documentation/places/web-service/details
        """
        query_params = {
            'place_id': place_id,
            'sessiontoken': token,
            'key': self.places_key,
            'fields': 'geometry,name,place_id,type,url'
        }
        url = ''.join([
            self.api_url,
            '/place/details/json',
            self.params_to_url_part(query_params)
        ])
        self._log(f'GET {url}')
        response = requests.get(url)
        if not 200 <= response.status_code < 300:
            raise GoogleMapsException(response=response)
        data = response.json()
        # https://developers.google.com/maps/documentation/places/web-service/details#PlacesDetailsStatus
        if data['status'] == 'OK':
            return data
        raise GoogleMapsException(response=response)

    def geocode_from_location(self, location: str, region: str = None) -> dict[str, any]:
        """
        See https://developers.google.com/maps/documentation/geocoding/requests-geocoding#geocoding-lookup
        """
        query_params = {
            'address': location,
            'key': self.geocoding_key,
        }
        if region is not None:
            query_params['region'] = region
        url = ''.join([
            self.api_url,
            '/geocode/json',
            self.params_to_url_part(query_params)
        ])
        self._log(f'GET {url}')
        response = requests.get(url)
        if not 200 <= response.status_code < 300:
            raise GoogleMapsException(response=response)
        data = response.json()
        # https://developers.google.com/maps/documentation/geocoding/requests-geocoding#StatusCodes
        if data['status'] == 'OK':
            return data
        raise GoogleMapsException(response=response)

    def reverse_geocode(self, latlng: str) -> dict[str, any]:
        """
        See https://developers.google.com/maps/documentation/geocoding/requests-reverse-geocoding
        """
        query_params = {
            'latlng': latlng,
            'key': self.geocoding_key,
            'result_type': '|'.join([
                'street_address',
                'route',
                'intersection',
                'political',
                'administrative_area_level_1',
                'administrative_area_level_2',
                'administrative_area_level_3',
                'administrative_area_level_4',
                'administrative_area_level_5',
                'administrative_area_level_6',
                'administrative_area_level_7',
                'colloquial_area',
                'locality',
                'sublocality',
                'neighborhood',
                'premise',
                'subpremise',
                'natural_feature',
                'airport',
                'park',
                'point_of_interest',
            ])
        }
        url = ''.join([
            self.api_url,
            '/geocode/json',
            self.params_to_url_part(query_params)
        ])
        self._log(f'GET {url}')
        response = requests.get(url)
        if not 200 <= response.status_code < 300:
            raise GoogleMapsException(response=response)
        data = response.json()
        # https://developers.google.com/maps/documentation/geocoding/requests-reverse-geocoding#reverse-status-codes
        if data['status'] == 'OK' or data['status'] == 'ZERO_RESULTS':
            # Zero results is okay because some latitude and longitude
            # combinations have no geocoding information,
            # especially in very remote parts of the planet
            return data
        raise GoogleMapsException(response=response)
