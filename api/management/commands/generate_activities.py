import datetime
import math
import random
import sys

from django.core.management.base import BaseCommand
from django.utils import timezone
from api.enums import ActivityType
from api.models import User, Activity, Post, Playlist
from api.models.experience import Experience
from api.models.comment import Comment

"""
Usage:
    ./manage.py generate_activities

    Creating aggregate activities saves each activity individually and
    takes significantly longer.
"""

class Command(BaseCommand):

    def print_progress(self, on: int, outof: int):
        progress = on / outof
        progress *= 100
        progress = math.floor(progress)
        sys.stdout.write("Progress: %s%%   \r" % (progress))

    def handle(self, *args, **options):
        user_id = input('User ID: ')
        if user_id is None or user_id.strip() == '':
            print('User ID required')
            exit(1)
        user_id = int(user_id)
        user: User = User.objects.filter(pk=user_id).first()
        if user is None:
            print('User not found, or no response from API')
            exit(1)

        print(f'  Username:  {user.username}')
        print(f'  Email: {user.email}')

        num_activities = int(input('Number of activities: '))
        is_push = input('Mark as push notifications? (y/N): ') == 'y'
        activities = []
        for i in range(num_activities):
            if i % 10 == 0:
                self.print_progress(on=i, outof=num_activities)
            activity_type = random.choice(ActivityType.choices)

            activity = Activity()
            related_users = User.objects.all()[0:5]
            activity.related_user = random.choice(related_users)
            activity.related_time = timezone.now() + datetime.timedelta(days=1)
            activity.user = user
            activity.type = activity_type[0]
            activity.is_push = is_push

            match activity.type:
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
                    pass
                    # experience_stacks = ExperienceStack.objects.all()[0:5]
                    # activity.experience_stack = random.choice(experience_stacks)
                    # activity.comment = Comment.objects.filter(experience_stack=activity.experience_stack).first()
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
                    # experience_stacks = ExperienceStack.objects.all()[0:5]
                    # activity.experience_stack = random.choice(experience_stacks)
                    pass
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
                    # experience_stacks = ExperienceStack.objects.all()[0:5]
                    # activity.experience_stack = random.choice(experience_stacks)
                    # activity.comment = Comment.objects.filter(experience_stack=activity.experience_stack).first()
                    pass
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
            activities.append(activity)
        sys.stdout.write("Creating...\n")
        Activity.objects.bulk_create(activities)
