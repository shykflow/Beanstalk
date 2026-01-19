from django.core.management.base import BaseCommand

from api.models import (
    User,
)

class Command(BaseCommand):

    def handle(self, *args, **options):
        user_id = int(input('User id: ').strip())
        user: User = User.objects.filter(pk=user_id).first()
        if user is None:
            print('User not found')
            exit(1)

        print('')
        print(f'{user.username} | {user.email}')
        print('')

        to_follow_str = input('Number of new people to follow: ') \
            .strip()

        to_follow = 0
        try:
            to_follow = int(to_follow_str)
        except:
            print('Invalid number')
            exit(1)

        print('')
        print('Followed these people:')
        users_to_follow = User.objects \
            .exclude(pk=user_id). \
            exclude(pk__in=user.follows.all()) \
            .order_by('?')
        users_to_follow = users_to_follow[0:to_follow]
        for u in users_to_follow:
            print(f' - {u.username} | {u.email}')
            user.follows.add(u)
