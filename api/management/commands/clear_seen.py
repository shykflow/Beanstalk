from django.core.management.base import BaseCommand

from api.models import User

class Command(BaseCommand):

    def handle(self, *args, **options):
        user_id = int(input('User id: ').strip())
        user: User = User.objects.filter(pk=user_id).first()
        if user is None:
            print('User not found')
            exit(1)
        print(f'{user.username} - {user.email}')
        clear_seen_experiences = input('Clear seen experiences  [y/N]: ').strip().lower() == 'y'
        clear_seen_playlists = input('Clear seen playlists [y/N]: ').strip().lower() == 'y'
        clear_seen_posts = input('Clear seen posts [y/N]: ').strip().lower() == 'y'
        if clear_seen_experiences:
            print('')
            print('Clearing seen experiences')
            user.seen_experiences.clear()
        if clear_seen_playlists:
            print('')
            print('Clearing seen playlists')
            user.seen_playlists.clear()
        if clear_seen_posts:
            print('')
            print('Clearing seen posts')
            user.seen_posts.clear()
        print('')
