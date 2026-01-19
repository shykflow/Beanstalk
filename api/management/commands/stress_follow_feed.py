import random
from django.core.management.base import BaseCommand

from api.models import (
    Playlist,
    Experience,
    Post,
    User,
)
from api.utils.command_line_spinner import CommandLineSpinner
import api.utils.commands as commands

class Command(BaseCommand):

    def handle(self, *args, **options):
        words = commands.populate_words()
        playlists_to_create: list[Playlist] = []
        experiences_to_create = []
        posts_to_create = []
        user_id = input("Enter a user's ID: ")
        try:
            user_id = int(user_id)
            user: User = User.objects.get(pk=user_id)
        except:
            return 'Please enter a valid user ID'
        followed_users = user.follows.all()
        for followed_user in followed_users:
            for _ in range(random.randint(500, 1000)):
                experiences_to_create.append(
                    Experience(
                        created_by=followed_user,
                        name=' '.join(commands.get_random_words(
                            words,
                            length=random.randint(1, 8),
                            add_new_lines=False,
                        )).capitalize(),
                        description=' '.join(commands.get_random_words(
                            words,
                            length=random.randint(10, 100),
                            add_new_lines=False,
                        )).capitalize(),
                    )
                )
                playlists_to_create.append(
                    Playlist(
                        created_by=followed_user,
                        name=' '.join(commands.get_random_words(
                            words,
                            length=random.randint(1, 8),
                            add_new_lines=False,
                        )).capitalize(),
                        description=' '.join(commands.get_random_words(
                            words,
                            length=random.randint(10, 100),
                            add_new_lines=False,
                        )).capitalize(),
                    )
                )
                posts_to_create += [
                    Post(
                        created_by=followed_user,
                        text=' '.join(commands.get_random_words(
                            words,
                            length=random.randint(10, 100),
                            add_new_lines=False,
                        )).capitalize(),
                        experience=random.choice(experiences_to_create),
                    ),
                    Post(
                        created_by=followed_user,
                        text=' '.join(commands.get_random_words(
                            words,
                            length=random.randint(10, 100),
                            add_new_lines=False,
                        )).capitalize(),
                        playlist=random.choice(playlists_to_create),
                    ),
                ]

        with CommandLineSpinner(label='Bulk Create experiences'):
            random.shuffle(experiences_to_create)
            Experience.objects.bulk_create(experiences_to_create)
        print('...Done')
        print('')

        with CommandLineSpinner('Bulk Create playlists'):
            random.shuffle(playlists_to_create)
            Playlist.objects.bulk_create(playlists_to_create)
            for playlist in playlists_to_create:
                playlist.experiences.add(
                    *random.sample(
                        experiences_to_create,
                        k=random.randint(1, 10)
                    )
                )
        print('...Done')
        print('')

        with CommandLineSpinner(label='Bulk Create posts'):
            random.shuffle(posts_to_create)
            Post.objects.bulk_create(posts_to_create)
        print('...Done')
        print('')
