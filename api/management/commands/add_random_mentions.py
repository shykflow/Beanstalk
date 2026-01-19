from django.core.management.base import BaseCommand
import random

from api.models import (
    Playlist,
    Experience,
    Comment,
    Post,
    User,
)

from api.utils.command_line_spinner import CommandLineSpinner

class Command(BaseCommand):

    def add_tag(self, user: User, text: str) -> str:
        if text is None:
            text = ''
        tag = f'<@{user.id}>'
        if tag in text:
            return text
        words = text.split(' ')
        if len(words) == 0:
            return tag
        position = random.randint(0, len(words))
        words.insert(position, tag)
        return ' '.join(words)


    def handle(self, *args, **options):
        with CommandLineSpinner(label='Getting Users'):
            users = list(User.objects.filter(is_superuser=False, email_verified=True))

        with CommandLineSpinner(label='Getting Playlists'):
            num_playlists = Playlist.objects.all().count()
            limit_playlists = int(num_playlists * 0.5)
            playlists = list(Playlist.objects.all()[:limit_playlists])

        with CommandLineSpinner(label='Getting Experiences'):
            num_experience = Experience.objects.all().count()
            limit_experience = int(num_experience * 0.5)
            experiences = list(Experience.objects.all()[:limit_experience])

        with CommandLineSpinner(label='Getting Posts'):
            num_posts = Post.objects.all().count()
            limit_posts = int(num_posts * 0.25)
            posts = list(Post.objects.all()[:limit_posts])

        with CommandLineSpinner(label='Getting Comments'):
            num_comments = Comment.objects.all().count()
            limit_comments = int(num_comments * 0.17)
            comments = list(Comment.objects.all()[:limit_comments])

        label = f'Inserting mentions into {limit_playlists} out of {num_playlists} Playlists'
        with CommandLineSpinner(label=label):
            for obj in playlists:
                user = random.choice(users)
                obj.description = self.add_tag(user, obj.description)
                obj.save()

        label = f'Inserting mentions into {limit_experience} out of {num_experience} Experiences'
        with CommandLineSpinner(label=label):
            for obj in experiences:
                user = random.choice(users)
                obj.description = self.add_tag(user, obj.description)
                obj.save()

        label = f'Inserting mentions into {limit_posts} out of {num_posts} Posts'
        with CommandLineSpinner(label=label):
            for obj in posts:
                user = random.choice(users)
                obj.text = self.add_tag(user, obj.text)
                obj.save()

        label = f'Inserting mentions into {limit_comments} out of {num_comments} Comments'
        with CommandLineSpinner(label=label):
            for obj in comments:
                user = random.choice(users)
                obj.text = self.add_tag(user, obj.text)
                obj.save()
