from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone
from os import makedirs, path

"""
Usage:
    ./manage.py generate_erd
    ./manage.py generate_erd --arrow-shape normal
    ./manage.py generate_erd --path my_custom_path
    ./manage.py generate_erd --arrow-shape normal --path my_custom_path
"""

class Command(BaseCommand):
    def add_arguments(self, parser):
        # All --arrow-shape options:
        # https://github.com/django-extensions/django-extensions/blob/main/django_extensions/management/commands/graph_models.py#L178
        parser.add_argument('--arrow-shape', type=str, default='diamond')
        parser.add_argument('--path', type=str, default='erd')

    def handle(self, *args, **options):
        if not path.exists(options['path']):
            makedirs(options['path'])

        file_path = f"{options['path']}/{timezone.now().strftime('%b-%d-%Y-%I-%M-%p-%Z')}.jpg"
        call_command('graph_models', all_applications=True, arrow_shape=options['arrow_shape'], outputfile=file_path)
