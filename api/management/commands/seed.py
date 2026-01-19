import random

from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandParser
from django.utils import timezone

from api.models import (
    Playlist,
    PlaylistUser,
    PlaylistCostRating,
    PlaylistStarRating,
    CategoryMapping,
    ExperienceCostRating,
    ExperienceStarRating,
    Post,
    Comment,
    Experience,
    ExperienceStack,
    User,
    UserFollow,
)
import api.utils.commands as commands
from api.enums import UserType
from api.models.app_color import AppColor
from lf_service.user import LifeFrameUserService
from lf_service.util import LifeFrameUtilService
from lf_service.models import Category
from lf_service.category import LifeFrameCategoryService



class Command(BaseCommand):
    lf_user_service = LifeFrameUserService()
    lf_util_service = LifeFrameUtilService()
    lf_category_service = LifeFrameCategoryService()
    multiply_by: int = 1
    extra_random_users: int = 4

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            '--multiply-by',
            type=int,
            default=1,
            help="Multiply the number of records created")

        parser.add_argument(
            '--extra-random-users',
            type=int,
            default=4,
            help='Create this many more users with random usernames')
        return super().add_arguments(parser)

    def get_random_hex_string(self, characters: int) -> str:
        return "".join(random.choice("ABCDEF0123456789") for i in range(characters))

    def test_lifeframe_connection(self):
        try:
            Command.lf_util_service.healthcheck()
        except:
            print('Could not get a response from LifeFrame')
            exit()

    def set_vars_from_command_line(self, options: dict[str, any]):
        Command.multiply_by: int = options['multiply_by']
        if Command.multiply_by < 1:
            raise Exception('--multiply-by must be >= 1')
        Command.extra_random_users: int = options['extra_random_users']
        if Command.extra_random_users < 0:
            raise Exception('--extra-random-users must be >= 0')

    def handle(self, *args, **options):
        self.set_vars_from_command_line(options)
        self.test_lifeframe_connection()
        self.words = commands.populate_words()
        to_make = {
            'experience_stacks': 10 * Command.multiply_by,
            'users': [
                'userA',
                'userB',
                'userC',
                'userD',
                'userE_who_has_a_medium_length_name',
                'userF_who_has_a_really_long_name_we_need_to_handle_in_the_mobile_app',
                'admin',
                'data_entry',
                'verifieduser',
                'partneruser',
                'banneduser',
                # ... more users can be added with the command line arg --extra-random-users
                # which defaults to 4
            ],

            # The requested number, not the actual number. Some duplicates can be removed
            # after querying.
            'category_maps': 20 * Command.multiply_by,

            # per user
            'experiences': 5 * Command.multiply_by,
            'playlists': 3 * Command.multiply_by,

            'app_colors': [
                # These are all of Google Material's basic colors
                '#FFEB3B', # yellow
                '#795548', # brown
                '#F44336', # red
                '#2196F3', # blue
                '#4CAF50', # green
                '#FFC107', # amber
                '#00BCD4', # cyan
                '#3F51B5', # indigo
                '#CDDC39', # lime
                '#FF9800', # orange
                '#E91E63', # pink
                '#9C27B0', # purple
                '#009688', # teal
            ],
        }

        for _ in range(Command.extra_random_users):
            words = commands.get_random_words(self.words, length=2)
            random_username = '_'.join(words)
            random_username = ''.join(random_username.split())
            random_username = ''.join(random_username.split("'"))
            random_username = ''.join(random_username.split('"'))
            to_make['users'].append(random_username)

        users: list[User] = []
        experiences: list[Experience] = []
        experience_stacks: list[ExperienceStack] = []
        playlists: list[Playlist] = []
        experience_posts: list[Post] = []
        playlist_posts: list[Post] = []
        app_posts: list[Post] = []
        category_picker_maps: list[CategoryMapping] = []

        print('CategoryMappings')
        # Getting category mappings in chunks because LifeFrame has a limit 100 but this
        # script can generate more than 100.
        # Not guaranteed to get the number requested, duplicates
        # will be removed after chunks are requested.
        categories: list[Category] = []
        categories_to_get = to_make['category_maps']
        categories_to_get_chunk_size = 100
        while categories_to_get > 0:
            prev_ids = [c.id for c in categories]
            new_categories = Command.lf_category_service.random(limit=categories_to_get_chunk_size, all=True)
            # remove duplicates
            categories += [c for c in new_categories if c.id not in prev_ids]
            categories_to_get -= categories_to_get_chunk_size
        sequence = 0
        category: Category
        for category in categories:
            if not CategoryMapping.objects.filter(category_id=category.id).exists():
                c_map = CategoryMapping.objects.create(
                    category_id=category.id,
                    picker_sequence=sequence,
                    show_in_picker=random.randint(0, 4) == 0)
                category_picker_maps.append(c_map)
            commands.print_progress(sequence, len(categories) - 1)
            sequence += 1
        print([c.id for c in categories])
        Command.lf_category_service.mark_has_content([c.id for c in categories])
        print(f'  Created {len(category_picker_maps)} CategoryMappings')
        print('')


        print('AppColors')
        color: str
        for color in to_make['app_colors']:
            AppColor.objects.get_or_create(color=color)
        print(f'  Created {len(to_make["app_colors"])} AppColors')
        print('')

        for j in range(to_make['experience_stacks']):
            name_words = commands.get_random_words(
                self.words,
                length=random.randint(2, 4))
            description_words = commands.get_random_words(
                self.words,
                length=random.randint(5, 40),
                add_new_lines=True)
            experience_stack = ExperienceStack(
                name=" ".join(name_words).capitalize(),
                description=" ".join(description_words).capitalize())
            experience_stack.save()
            experience_stacks.append(experience_stack)
        print(f'  Created {len(experience_stacks)} ExperienceStacks')
        print('')

        for i, username in enumerate(to_make['users']):
            user: User
            user, user_created = User.objects.get_or_create(
                username=username,
                email=f'{username}@test.com')
            if user_created:
                user.set_password('Test1234$')
                user.email_verified = True
                lifeframe_user = Command.lf_user_service.create()
                user.life_frame_id = lifeframe_user.id
                user.birthdate = timezone.datetime(1990, 1, 1, tzinfo=timezone.utc)
                if username == 'admin':
                    group_name = 'Admin'
                    group: Group = Group.objects.filter(name=group_name).first()
                    if group is None:
                        print(f'    DID NOT add the user with username "{user.username}" to the "{group_name}" group, ' +\
                            "couldn't find the group in the database")
                    else:
                        print(f'    Added the user with username "{user.username}" to the "Admin" group')
                        group.user_set.add(user)
                    user.is_staff = True
                    user.notify_about_new_content_reports = True
                elif username == 'data_entry':
                    group_name = 'Data Entry'
                    group: Group = Group.objects.filter(name=group_name).first()
                    if group is None:
                        print(f'    DID NOT add the user with username "{user.username}" to the "{group_name}" group, ' + \
                            "couldn't find the group in the database")
                    else:
                        print(f'    Added the user with username "{user.username}" to the "Admin" group')
                        group.user_set.add(user)
                    user.is_staff = True
                elif username == 'verifieduser':
                    user.user_type = UserType.VERIFIED
                elif username == 'partneruser':
                    user.user_type = UserType.PARTNER
                elif username == 'banneduser':
                    user.is_active = False
                user.save()
            print(f"  User: {user} with life_frame_id: {user.life_frame_id}")
            users.append(user)

            for j in range(to_make['playlists']):
                name_words = commands.get_random_words(
                    self.words,
                    length=random.randint(2, 4))
                description_words = commands.get_random_words(
                    self.words,
                    length=random.randint(5, 40),
                    add_new_lines=True)                
                today = timezone.now()
                day_offset = random.randint(-31, 31)
                timedelta = timezone.timedelta(days=day_offset)
                start_time = today + timedelta
                if random.randint(0, 5) == 0:
                    end_time = today + timedelta + timezone.timedelta(days=1)
                else:
                    end_time = today + timedelta

                playlist = Playlist(
                    created_by=user,
                    name=" ".join(name_words).capitalize(),
                    description=" ".join(description_words).capitalize(),
                    start_time=start_time,
                    end_time=end_time)
                playlist.save()
                playlists.append(playlist)

            for j in range(to_make['experiences']):
                name_words = commands.get_random_words(
                    self.words,
                    length=random.randint(2, 4))
                description_words = commands.get_random_words(
                    self.words,
                    length=random.randint(5, 40),
                    add_new_lines=True)
                add_more_categories = True
                # Get random categories to add to this experience.
                # Will always insert at least 1.
                exp_category_ids = []
                while add_more_categories:
                    exp_category_id_to_add = random.choice(categories).id
                    if exp_category_id_to_add not in exp_category_ids:
                        exp_category_ids.append(exp_category_id_to_add)
                    if random.randint(0, 1) == 1:
                        add_more_categories = False
                today = timezone.now()
                day_offset = random.randint(-31, 31)
                timedelta = timezone.timedelta(days=day_offset)
                start_time = today + timedelta
                if random.randint(0, 5) == 0:
                    end_time = today + timedelta + timezone.timedelta(days=1)
                else:
                    end_time = today + timedelta

                experience = Experience(
                    created_by=user,
                    name=" ".join(name_words).capitalize(),
                    description=" ".join(description_words).capitalize(),
                    categories=exp_category_ids,
                    start_time=start_time,
                    end_time=end_time)
                experience.save()
                experiences.append(experience)

        print(f'  Created {len(users)} Users')
        print('')
        print(f'  Created {len(experiences)} Experiences')
        print('')
        print(f'  Created {len(playlists)} Playlists')
        print('')

        print('Randomly inserting Experiences into ExperienceStacks')
        for i, cs in enumerate(experience_stacks):
            experiences_to_add = []
            for experience in experiences:
                associate = random.randint(0, 9) == 0
                if associate:
                    experiences_to_add.append(experience.id)
            cs.experiences.add(*experiences_to_add)
            commands.print_progress(i, len(experience_stacks) - 1)
        print('')
        print('')

        print('Randomly inserting Experiences into Playlists')
        for i, playlist in enumerate(playlists):
            experiences_to_add = []
            for experience in experiences:
                associate = random.randint(0, 9) == 0
                if associate:
                    experiences_to_add.append(experience.id)
            playlist.experiences.add(*experiences_to_add)
            commands.print_progress(i, len(playlists) - 1)
        print('')
        print('')

        print('ExperienceStack Follows')
        for i, cs in enumerate(experience_stacks):
            user_ids_to_add = []
            for user in users:
                follow = random.randint(0, 9) == 0
                if follow:
                    user_ids_to_add.append(user.id)
            commands.print_progress(i, len(experience_stacks) - 1)
        print('')
        print('')

        print('Playlist Follows')
        for i, playlist in enumerate(playlists):
            follows_to_create = []
            for user in users:
                follows_to_create.append(PlaylistUser(
                    user=user,
                    playlist=playlist))
            PlaylistUser.objects.bulk_create(follows_to_create)
            commands.print_progress(i, len(playlists) - 1)
        print('')
        print('')

        print('ExperiencePosts')
        for i, user in enumerate(users):
            posts_to_create = []
            for experience in experiences:
                should_post = random.randint(0, 9) == 0
                if should_post:
                    text_words = commands.get_random_words(
                        self.words,
                        length=random.randint(5, 40),
                        add_new_lines=True)
                    name_words = commands.get_random_words(
                        self.words,
                        length=random.randint(2, 4))
                    experience_post = Post(
                        name=" ".join(name_words).capitalize(),
                        text=" ".join(text_words).capitalize(),
                        created_by=user,
                        experience=experience)
                    posts_to_create.append(experience_post)
                    experience_posts.append(experience_post)
            Post.objects.bulk_create(posts_to_create)
            commands.print_progress(i, len(users) - 1)
        print('')
        print('')

        print('PlaylistPosts')
        for i, user in enumerate(users):
            posts_to_create = []
            for playlist in playlists:
                should_post = random.randint(0, 9) == 0
                if should_post:
                    name_words = commands.get_random_words(
                        self.words,
                        length=random.randint(2, 4))
                    text_words = commands.get_random_words(
                        self.words,
                        length=random.randint(5, 40),
                        add_new_lines=True)
                    playlist_post = Post(
                        name=" ".join(name_words).capitalize(),
                        text=" ".join(text_words).capitalize(),
                        created_by=user,
                        playlist=playlist)
                    posts_to_create.append(playlist_post)
                    playlist_posts.append(playlist_post)
            Post.objects.bulk_create(posts_to_create)
            commands.print_progress(i, len(users) - 1)
        print('')
        print('')

        print('AppPosts')
        posts_to_create = []
        for i, user in enumerate(users):
            name_words = commands.get_random_words(
                self.words,
                length=random.randint(2, 4))
            text_words = commands.get_random_words(
                self.words,
                length=random.randint(5, 40),
                add_new_lines=True)
            app_post = Post(
                name=" ".join(name_words).capitalize(),
                text=" ".join(text_words).capitalize(),
                created_by=user)
            posts_to_create.append(app_post)
            app_posts.append(app_post)
            commands.print_progress(i, len(users) - 1)
        Post.objects.bulk_create(posts_to_create)
        print('')
        print('')

        print('UserFollows')
        for i, user in enumerate(users):
            follows_to_create = []
            for follower in users:
                should_follow = random.randint(0, 3) == 0 and user.id != follower.id
                if not should_follow:
                    continue
                # Not using bulk create, adding a duplicate follow
                # crashes the seed script but running the seed script
                # multiple times is useful. This also runs wicked fast
                # since this doesn't create a crazy amount of records.
                follow, _ = UserFollow.objects.get_or_create(
                    user=follower,
                    followed_user=user)
                follows_to_create.append(follow)
            commands.print_progress(i, len(users) - 1)
        print('')
        print('')

        print('ExperienceRatings')
        for i, experience in enumerate(experiences):
            cost_ratings_to_create = []
            star_ratings_to_create = []
            for user in users:
                should_rate = random.randint(0, 6) == 0
                if not should_rate:
                    continue
                user.accepted_experiences.add(experience)
                user.completed_experiences.add(experience)
                experience_cost_rating = ExperienceCostRating(
                    experience=experience,
                    created_by=user,
                    rating=random.randint(0, 4),
                )
                experience_star_rating = ExperienceStarRating(
                    experience=experience,
                    created_by=user,
                    rating=random.randint(1, 5),
                )
                cost_ratings_to_create.append(experience_cost_rating)
                star_ratings_to_create.append(experience_star_rating)
            ExperienceCostRating.objects.bulk_create(cost_ratings_to_create)
            ExperienceStarRating.objects.bulk_create(star_ratings_to_create)
            commands.print_progress(i, len(experiences) - 1)
        print('')
        print('')

        print('PlaylistRatings')
        for i, playlist in enumerate(playlists):
            cost_ratings_to_create = []
            star_ratings_to_create = []
            for user in users:
                should_rate = random.randint(0, 6) == 0
                if not should_rate:
                    continue
                user.accepted_playlists.add(playlist)
                user.completed_playlists.add(playlist)
                playlist_cost_rating = PlaylistCostRating(
                    playlist=playlist,
                    created_by=user,
                    rating=random.randint(0, 4),
                )
                playlist_star_rating = PlaylistStarRating(
                    playlist=playlist,
                    created_by=user,
                    rating=random.randint(1, 5),
                )
                cost_ratings_to_create.append(playlist_cost_rating)
                star_ratings_to_create.append(playlist_star_rating)
            PlaylistCostRating.objects.bulk_create(cost_ratings_to_create)
            PlaylistStarRating.objects.bulk_create(star_ratings_to_create)
            commands.print_progress(i, len(playlists) - 1)
        print('')
        print('')

        print('ExperienceLikes')
        for i, experience in enumerate(experiences):
            like_user_ids = []
            for user in users:
                should_like = random.randint(0, 3) == 0
                if not should_like:
                    continue
                like_user_ids.append(user.id)
            experience.likes.add(*like_user_ids)
            commands.print_progress(i, len(experiences) - 1)
        print('')
        print('')

        print('PlaylistLikes')
        for i, playlist in enumerate(playlists):
            like_user_ids = []
            for user in users:
                should_like = random.randint(0, 3) == 0
                if not should_like:
                    continue
                like_user_ids.append(user)
            playlist.likes.add(*like_user_ids)
            commands.print_progress(i, len(playlists) - 1)
        print('')
        print('')

        print('ExperiencePostLikes')
        for i, experience_post in enumerate(experience_posts):
            like_user_ids = []
            for user in users:
                should_like = random.randint(0, 3) == 0
                if not should_like:
                    continue
                like_user_ids.append(user.id)
            experience_post.likes.add(*like_user_ids)
            commands.print_progress(i, len(experience_posts) - 1)
        print('')
        print('')

        print('PlaylistPostLikes')
        for i, playlist_post in enumerate(playlist_posts):
            like_user_ids = []
            for user in users:
                should_like = random.randint(0, 3) == 0
                if not should_like:
                    continue
                like_user_ids.append(user.id)
            playlist_post.likes.add(*like_user_ids)
            commands.print_progress(i, len(playlist_posts) - 1)
        print('')
        print('')

        # This must be after all experiences are added to playlists
        print('PlaylistPostLikes')
        for playlist in playlists:
            playlist.update_aggregated_categories()
        print('')
        print('')

        print('ExperienceLocations')
        call_command('fill_mock_location_data', local=True)

        print('Finished.')
