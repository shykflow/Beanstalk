from time import sleep

from django.db.models import Q
from django.core.management.base import BaseCommand

from api.models import (
    Experience,
)
from api.services.google_maps import GoogleMapsService
from api.utils.commands import print_progress

class Command(BaseCommand):

    def handle(self, *args, **options):
        maps_service = GoogleMapsService()
        exp_qs = Experience.objects \
            .filter(location__isnull=False) \
            .filter(Q(latitude__isnull=True) | Q(longitude__isnull=True))
        exp_count = exp_qs.count()
        print(f'Found {exp_count} experiences.')
        print('Converting location to lat long . . .')
        exp: Experience
        progress = 0
        saved = 0
        skipped = 0
        for exp in exp_qs:
            progress += 1
            print_progress(
                on=progress,
                outof=exp_count,
                decimal_places=3,
                show_values=True)
            try:
                response_dict = maps_service.geocode_from_location(
                    exp.location,
                    region='us')
                first_result = response_dict['results'][0]
                location_dict = first_result['geometry']['location']
                latitude = location_dict['lat']
                longitude = location_dict['lng']
                # formatted_address = first_result['formatted_address']
                # exp.location = formatted_address
                exp.latitude = latitude
                exp.longitude = longitude
                exp.save()
                saved += 1
            except:
                skipped += 1
            sleep(0.01)
        print(f'Saved: {saved}')
        print(f'Skipped: {skipped}')

