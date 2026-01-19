import random

from django.core.management.base import BaseCommand

from api.models import (
    Playlist,
    Experience,
    Comment,
    Post,
    User,
)
from api.utils.command_line_spinner import CommandLineSpinner
import api.utils.commands as commands

class Command(BaseCommand):

    def handle(self, *args, **options):
        words = commands.populate_words()
        users = User.objects.all()
        playlists = Playlist.objects.all()
        experiences = Experience.objects.all()
        posts = Post.objects.all()
        comments = []
        replies = []

        print('PlaylistComments')
        for i, playlist in enumerate(playlists):
            for user in users:
                comments += [
                    Comment(
                        created_by=user,
                        text=' '.join(commands.get_random_words(
                            words,
                            length=random.randint(3, 50),
                            add_new_lines=False,
                        )).capitalize(),
                        playlist=playlist,
                    ) for _ in range(random.randint(100, 200))
                ]
            commands.print_progress(i, len(playlists) - 1)
        print('')
        print('')

        print('ExperienceComments')
        for i, experience in enumerate(experiences):
            for user in users:
                comments += [
                    Comment(
                        created_by=user,
                        text=' '.join(commands.get_random_words(
                            words,
                            length=random.randint(3, 50),
                            add_new_lines=False,
                        )).capitalize(),
                        experience=experience,
                    ) for _ in range(random.randint(100, 200))
                ]
            commands.print_progress(i, len(experiences) - 1)
        print('')
        print('')

        print('PostComments')
        for i, post in enumerate(posts):
            for user in users:
                comments += [
                    Comment(
                        created_by=user,
                        text=' '.join(commands.get_random_words(
                            words,
                            length=random.randint(3, 50),
                            add_new_lines=False,
                        )).capitalize(),
                        post=post,
                    ) for _ in range(random.randint(100, 200))
                ]
            commands.print_progress(i, len(posts) - 1)
        print('')
        print('')


        print('Replies (this can take a very long time)')
        for i, parent in enumerate(comments):
            for user in users:
                replies += [
                    Comment(
                        created_by=user,
                        text=' '.join(commands.get_random_words(
                            words,
                            length=random.randint(3, 50),
                            add_new_lines=False,
                        )).capitalize(),
                        parent=parent,
                        playlist=parent.playlist,
                        experience=parent.experience,
                        post=parent.post,
                    ) for _ in range(random.randint(0, 2))
                ]
            commands.print_progress(i, len(comments) - 1)
        print('')
        print('')

        with CommandLineSpinner(label='Bulk Create comments'):
            random.shuffle(comments)
            Comment.objects.bulk_create(comments)
        print('...Done')
        print('')

        with CommandLineSpinner(label='Bulk Create replies (this can take a very long time)'):
            random.shuffle(replies)
            Comment.objects.bulk_create(replies)
        print('...Done')
