import datetime
import random

from django.core.management.base import BaseCommand
from django.utils import timezone
from api.enums import ActivityType
from api.models import User, Device, Activity, Post, Playlist, UserFollow
from api.models.experience import Experience
from api.models.experience_stack import ExperienceStack
from api.models.comment import Comment
from api.services.firebase import FirebaseService

"""
Usage:
    ./manage.py send_test_notification
"""

class Command(BaseCommand):

    def handle(self, *args, **options):
        _user_id = input('User ID: ')
        if _user_id is None or _user_id.strip() == '':
            print('User ID required')
            exit(1)
        user_id = int(_user_id)
        user: User = User.objects.filter(pk=user_id).first()
        if user is None:
            print('User not found, or no response from API')
            exit(1)

        devices: list[Device] = Device.objects.filter(user=user)
        print(f'  Username:  {user.username}')
        print(f'  Email: {user.email}')
        if len(devices) == 0:
            print('No devices for this user')
            exit(0)
        for device in devices:
            print(f'  {device.details}')
            print()

        activity_type = input('''RECEIVED_MESSAGE = 0

MENTIONED_EXPERIENCE = 100
MENTIONED_PLAYLIST = 101
MENTIONED_EXPERIENCE_STACK = 102
MENTIONED_POST = 103
MENTIONED_COMMENT = 104

LIKED_EXPERIENCE = 200
LIKED_PLAYLIST = 201
LIKED_EXPERIENCE_STACK = 202
LIKED_POST = 203
LIKED_COMMENT = 204

COMMENTED_EXPERIENCE = 300
COMMENTED_PLAYLIST = 301
COMMENTED_EXPERIENCE_STACK = 302
COMMENTED_POST = 303
COMMENTED_COMMENT = 304

ACCEPTED_EXPERIENCE = 400
COMPLETED_EXPERIENCE = 401
ACCEPTED_PLAYLIST = 402
COMPLETED_PLAYLIST = 403

FOLLOW_NEW = 500
FOLLOW_ACCEPTED = 501
FOLLOW_REQUEST = 502

ADDED_TO_YOUR_PLAYLIST = 600
REMOVED_FROM_PLAYLIST = 601
ADDED_YOUR_EXPERIENCE_TO_PLAYLIST = 602

Select one: ''')
        activity = Activity()

        related_users = User.objects.all()[0:5]
        activity.related_user = random.choice(related_users)
        activity.type = activity_type
        activity.related_time = timezone.now() + datetime.timedelta(days=1)
        activity.user = user

        match ActivityType(int(activity_type)):
            # RECEIVED_MESSAGE
            case ActivityType.RECEIVED_MESSAGE:
                pass

            # MENTIONED_EXPERIENCE
            case ActivityType.MENTIONED_EXPERIENCE:
                experiences = Experience.objects.all()[0:5]
                activity.experience = random.choice(experiences)
            # MENTIONED_PLAYLIST
            case ActivityType.MENTIONED_PLAYLIST:
                playlists = Playlist.objects.all()[0:5]
                activity.playlist = random.choice(playlists)
            # MENTIONED_EXPERIENCE_STACK
            case ActivityType.MENTIONED_EXPERIENCE_STACK:
                experience_stacks = ExperienceStack.objects.all()[0:5]
                activity.experience_stack = random.choice(experience_stacks)
                activity.comment = Comment.objects.filter(experience_stack=activity.experience_stack).first()
            # MENTIONED_POST
            case ActivityType.MENTIONED_POST:
                posts = Post.objects.all()[0:5]
                activity.post = random.choice(posts)
            # MENTIONED_COMMENT
            case ActivityType.MENTIONED_COMMENT:
                comment = Comment.objects.all()[0:5]
                activity.comment = random.choice(comment)

            # LIKED_EXPERIENCE
            case ActivityType.LIKED_EXPERIENCE:
                experiences = Experience.objects.all()[0:5]
                activity.experience = random.choice(experiences)
            # LIKED_PLAYLIST
            case ActivityType.LIKED_PLAYLIST:
                playlists = Playlist.objects.all()[0:5]
                activity.playlist = random.choice(playlists)
            # LIKED_EXPERIENCE_STACK
            case ActivityType.LIKED_EXPERIENCE_STACK:
                experience_stacks = ExperienceStack.objects.all()[0:5]
                activity.experience_stack = random.choice(experience_stacks)
            # LIKED_POST
            case ActivityType.LIKED_POST:
                posts = Post.objects.all()[0:5]
                activity.post = random.choice(posts)
            # LIKED_COMMENT
            case ActivityType.LIKED_COMMENT:
                comment = Comment.objects.all()[0:5]
                activity.comment = random.choice(comment)

            # COMMENTED_EXPERIENCE
            case ActivityType.COMMENTED_EXPERIENCE:
                experiences = Experience.objects.all()[0:5]
                activity.experience = random.choice(experiences)
                activity.comment = Comment.objects.filter(playlist=activity.playlist).first()
            # COMMENTED_PLAYLIST
            case ActivityType.COMMENTED_PLAYLIST:
                playlists = Playlist.objects.all()[0:5]
                activity.playlist = random.choice(playlists)
                activity.comment = Comment.objects.filter(playlist=activity.playlist).first()
            # COMMENTED_EXPERIENCE_STACK
            case ActivityType.COMMENTED_EXPERIENCE_STACK:
                experience_stacks = ExperienceStack.objects.all()[0:5]
                activity.experience_stack = random.choice(experience_stacks)
                activity.comment = Comment.objects.filter(experience_stack=activity.experience_stack).first()
            # COMMENTED_POST
            case ActivityType.COMMENTED_POST:
                posts = Post.objects.all()[0:5]
                activity.post = random.choice(posts)
                activity.comment = Comment.objects.filter(post=activity.post).first()
            # COMMENTED_COMMENT
            case ActivityType.COMMENTED_COMMENT:
                comment = Comment.objects.all()[0:5]
                activity.comment = random.choice(comment)

            # ACCEPTED_EXPERIENCE
            case ActivityType.ACCEPTED_EXPERIENCE:
                experiences = Experience.objects.all()[0:5]
                activity.experience = random.choice(experiences)
            # COMPLETED_EXPERIENCE
            case ActivityType.COMPLETED_EXPERIENCE:
                experiences = Experience.objects.all()[0:5]
                activity.experience = random.choice(experiences)
            # ACCEPTED_PLAYLIST
            case ActivityType.ACCEPTED_PLAYLIST:
                playlists = Playlist.objects.all()[0:5]
                activity.playlist = random.choice(playlists)
            # COMPLETED_PLAYLIST
            case ActivityType.COMPLETED_PLAYLIST:
                playlists = Playlist.objects.all()[0:5]
                activity.playlist = random.choice(playlists)

            # FOLLOW_NEW
            case ActivityType.FOLLOW_NEW:
                pass
            # FOLLOW_ACCEPTED
            case ActivityType.FOLLOW_ACCEPTED:
                pass
            # FOLLOW_REQUEST
            case ActivityType.FOLLOW_REQUEST:
                pass

            # ADDED_TO_YOUR_PLAYLIST
            case ActivityType.ADDED_TO_YOUR_PLAYLIST:
                experiences = Experience.objects.all()[0:5]
                activity.experience = random.choice(experiences)
                playlists = Playlist.objects.all()[0:5]
                activity.playlist = random.choice(playlists)
            # REMOVED_FROM_PLAYLIST
            case ActivityType.REMOVED_FROM_PLAYLIST:
                playlists = Playlist.objects.all()[0:5]
                activity.playlist = random.choice(playlists)
                experiences = Experience.objects.all()[0:5]
                activity.experience = random.choice(experiences)
            # ADDED_YOUR_EXPERIENCE_TO_PLAYLIST
            case ActivityType.ADDED_YOUR_EXPERIENCE_TO_PLAYLIST:
                playlists = Playlist.objects.all()[0:5]
                activity.playlist = random.choice(playlists)
                experiences = Experience.objects.all()[0:5]
                activity.experience = random.choice(experiences)


        activity.save()

        firebase_service = FirebaseService()
        firebase_service.push_activity_to_user(activity)
