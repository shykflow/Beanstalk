import random

from django.core.management.base import BaseCommand

from api.models import Experience
from api.services.google_maps import GoogleMapsService
from api.utils.command_line_spinner import CommandLineSpinner

from api.utils.commands import print_progress

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        experiences_qs = Experience.objects \
            .filter(latitude__isnull=False, longitude__isnull=False)
        total = experiences_qs.count()
        service = GoogleMapsService()
        with CommandLineSpinner(label='Setting location name from lat-long', bypass_spinning=True):
            index = 0
            exp: Experience
            for exp in experiences_qs:
                index += 1
                print_progress(on=index, outof=total)
                latlng = f'{exp.latitude},{exp.longitude}'
                response = service.reverse_geocode(latlng)
                results = response['results']
                if len(results) == 0:
                    continue
                result = results[0]
                exp.location = result['formatted_address']
                exp.save()
