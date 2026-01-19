from django.core.management.base import BaseCommand
import random

from api.models import (
    Playlist,
    Post,
    Comment,
    Experience,
    User,
)
import api.utils.commands as commands
from api.utils.command_line_spinner import CommandLineSpinner

class Command(BaseCommand):


    def handle(self, *args, **options):
        words = commands.populate_words()
        with CommandLineSpinner(label='Getting Users'):
            users = list(User.objects.filter(is_superuser=False, email_verified=True))
        with CommandLineSpinner(label='Getting Experiences'):
            experiences = list(Experience.objects.all())
        with CommandLineSpinner(label='Getting Experience Posts'):
            experience_posts = list(Post.objects.filter(experience__isnull=False))
        with CommandLineSpinner(label='Getting Experiences'):
            playlists = list(Playlist.objects.all())
        with CommandLineSpinner(label='Getting Playlist Posts'):
            playlist_posts = list(Post.objects.filter(playlist__isnull=False))
        with CommandLineSpinner(label='Getting App Posts'):
            app_posts = list(Post.objects.filter(playlist__isnull=True, experience__isnull=True))


        with CommandLineSpinner(label='Creating Experience Comments'):
            for i, experience in enumerate(experiences):
                _experience_comments: list[Comment] = []
                _parent_comments: list[Comment] = []
                for user in users:
                    should_like = random.randint(0, 4) == 0 and _experience_comments != []
                    if should_like:
                        experience_comment = random.choice(_experience_comments)
                        experience_comment.likes.add(user)
                    should_comment = random.randint(0, 3) == 0
                    if not should_comment:
                        continue
                    text_words = commands.get_random_words(
                        words,
                        length=random.randint(5, 40),
                        add_new_lines=True)
                    parent: Comment = None
                    is_reply = _parent_comments != [] and random.randint(0, 1) == 0
                    if is_reply:
                        parent = random.choice(_parent_comments)
                    experience_comment = Comment(
                        parent=parent,
                        text=" ".join(text_words).capitalize(),
                        created_by=user,
                        experience=experience)
                    experience_comment.save()
                    _experience_comments.append(experience_comment)
                    if not is_reply:
                        _parent_comments.append(experience_comment)
                commands.print_progress(i, len(experiences) - 1)

        with CommandLineSpinner(label='Creating Experience Post Comments'):
            for i, experience_post in enumerate(experience_posts):
                _experience_post_comments: list[Comment] = []
                _parent_comments: list[Comment] = []
                for user in users:
                    should_like = random.randint(0, 4) == 0 and _experience_comments != []
                    if should_like:
                        experience_comment = random.choice(_experience_comments)
                        experience_comment.likes.add(user)
                    should_comment = random.randint(0, 3) == 0
                    if not should_comment:
                        continue
                    text_words = commands.get_random_words(
                        words,
                        length=random.randint(5, 40),
                        add_new_lines=True)
                    parent: Comment = None
                    is_reply = _parent_comments != [] and random.randint(0, 1) == 0
                    if is_reply:
                        parent = random.choice(_parent_comments)
                    experience_post_comment = Comment(
                        parent=parent,
                        text=" ".join(text_words).capitalize(),
                        created_by=user,
                        post=experience_post)
                    experience_post_comment.save()
                    _experience_post_comments.append(experience_post_comment)
                    if not is_reply:
                        _parent_comments.append(experience_post_comment)
                commands.print_progress(i, len(experience_posts) - 1)

        with CommandLineSpinner(label='Creating Playlist Comments'):
            for i, playlist in enumerate(playlists):
                _playlist_comments: list[Comment] = []
                _parent_comments: list[Comment] = []
                for user in users:
                    should_comment = random.randint(0, 3) == 0
                    if not should_comment:
                        continue
                    text_words = commands.get_random_words(
                        words,
                        length=random.randint(5, 40),
                        add_new_lines=True)
                    parent: Comment = None
                    is_reply = _parent_comments != [] and random.randint(0, 1) == 0
                    if is_reply:
                        parent = random.choice(_parent_comments)
                    playlist_comment = Comment(
                        parent=parent,
                        text=" ".join(text_words).capitalize(),
                        created_by=user,
                        playlist=playlist)
                    playlist_comment.save()
                    _playlist_comments.append(playlist_comment)
                    if not is_reply:
                        _parent_comments.append(playlist_comment)
                commands.print_progress(i, len(playlists) - 1)

        with CommandLineSpinner(label='Creating Playlist Post Comments'):
            for i, playlist_post in enumerate(playlist_posts):
                _playlist_post_comments: list[Comment] = []
                _parent_comments: list[Comment] = []
                for user in users:
                    should_comment = random.randint(0, 3) == 0
                    if not should_comment:
                        continue
                    parent: Comment = None
                    is_reply = _parent_comments != [] and random.randint(0, 1) == 0
                    if is_reply:
                        parent = random.choice(_parent_comments)
                    text_words = commands.get_random_words(
                            words,
                            length=random.randint(5, 40),
                            add_new_lines=True)
                    playlist_post_comment = Comment(
                        parent=parent,
                        text=" ".join(text_words).capitalize(),
                        created_by=user,
                        post=playlist_post)
                    playlist_post_comment.save()
                    _playlist_post_comments.append(playlist_post_comment)
                    if not is_reply:
                        _parent_comments.append(playlist_post_comment)
                commands.print_progress(i, len(playlist_posts) - 1)

        with CommandLineSpinner(label='Creating App Post Comments'):
            for i, app_post in enumerate(app_posts):
                _app_post_comments: list[Comment] = []
                _parent_comments: list[Comment] = []
                for user in users:
                    should_comment = random.randint(0, 3) == 0
                    if not should_comment:
                        continue
                    parent: Comment = None
                    is_reply = _parent_comments != [] and random.randint(0, 1) == 0
                    if is_reply:
                        parent = random.choice(_parent_comments)
                    text_words = commands.get_random_words(
                            words,
                            length=random.randint(5, 40),
                            add_new_lines=True)
                    app_post_comment = Comment(
                        parent=parent,
                        text=" ".join(text_words).capitalize(),
                        created_by=user,
                        post=app_post)
                    app_post_comment.save()
                    _app_post_comments.append(app_post_comment)
                    if not is_reply:
                        _parent_comments.append(app_post_comment)
                commands.print_progress(i, len(app_posts) - 1)
        print('')
