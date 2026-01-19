from django.core.management.base import BaseCommand
import random

from api.models import (
    CategoryMapping,
    User,
)
import api.utils.commands as commands
from api.utils.command_line_spinner import CommandLineSpinner
from sponsorship.models import (
    CategorySponsorship,
)

class Command(BaseCommand):


    def handle(self, *args, **options):
        with CommandLineSpinner(label='Getting Users'):
            users = list(User.objects.filter(is_superuser=False, email_verified=True))

        with CommandLineSpinner(label='Getting random CategoryMappings'):
            cat_maps_count = CategoryMapping.objects.count()
            cat_maps_limit = int(cat_maps_count * 0.2)
            cat_maps = CategoryMapping.objects \
                .all() \
                .order_by('?') \
                [:cat_maps_limit]
            sponsorships_to_create = cat_maps.count()

        with CommandLineSpinner(label=f"Building {sponsorships_to_create} CategoryMapping sponsorships"):
            for cat_map in cat_maps:
                user = random.choice(users)
                sponsorship, _ = CategorySponsorship.objects.get_or_create(
                    user=user,
                    category_id=cat_map.category_id)
                cat_map.sponsorship = sponsorship
                cat_map.save()
