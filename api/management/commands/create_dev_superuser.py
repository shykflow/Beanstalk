from django.core.management.base import BaseCommand

from api.models import User


class Command(BaseCommand):

    def handle(self, *args, **options):
        superuser = User.objects.filter(username='asdf').first()
        if superuser is not None:
            superuser.delete()
            print('Deleted old superuser')
        User.objects.create_superuser('asdf', 'asdf@asdf.com', 'asdf')
        print('Created superuser:')
        print('  username: asdf')
        print('  password: asdf')
        print('  email:    asdf@asdf.com')
        print('')
