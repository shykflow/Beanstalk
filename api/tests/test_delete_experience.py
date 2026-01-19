import colorama
import datetime

from rest_framework import status

from api.models import (
    Playlist,
    Experience,
    ExperienceAccept,
    ExperienceSave,
    User,
    UserFollow,
)
from api.testing_overrides import GlobalTestCredentials, LifeFrameCategoryOverrides
from . import SilenceableAPITestCase

class Test(SilenceableAPITestCase):
    followed_user: User
    experience: Experience
    experience_from_followed: Experience


    def setUpTestData():
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        relevant_data = LifeFrameCategoryOverrides.relevant
        relevant_category_groups = relevant_data['category_groups']
        relevant_categories = relevant_data['categories']
        relevant_category = relevant_categories[0]
        Test.followed_user = User.objects.create(
            username = 'followed_user',
            email = 'followed_user@email.com',
            email_verified = True)
        UserFollow.objects.create(
            user = GlobalTestCredentials.user,
            followed_user = Test.followed_user,
            created_at = now)
        Test.experience = Experience.objects.create(
            name='Owned experience',
            created_by=GlobalTestCredentials.user)
        Test.experience_from_followed = Experience.objects.create(
            name=relevant_category.name,
            created_by=Test.followed_user,
            categories=[relevant_category.id])


    def setUp(self):
        super().setUp()
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {GlobalTestCredentials.token}')


    def test_soft_delete_happens(self):
        # ORM usage test
        exp_soft_delete_1 = Experience.objects.create(
            name='will_soft_delete_1',
            created_by=GlobalTestCredentials.user)
        self.assertIsNotNone(Experience.objects.filter(pk=exp_soft_delete_1.pk).first())
        exp_soft_delete_1.delete()
        self.assertIsNone(Experience.objects.filter(pk=exp_soft_delete_1.pk).first())

        # API usage test
        exp_soft_delete_2 = Experience.objects.create(
            name='will_soft_delete_2',
            created_by=GlobalTestCredentials.user)

        self.assertIsNone(exp_soft_delete_2.deleted_at)
        response = self.client.delete(f'/experiences/{exp_soft_delete_2.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        exp_soft_delete_2.refresh_from_db()

        # Delete endpoint properly set the deleted_at
        self.assertIsNotNone(exp_soft_delete_2.deleted_at)

        # Attempt to double delete the same experience
        response = self.client.delete(f'/experiences/{exp_soft_delete_2.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Get the deleted experience
        response = self.client.get(f'/experiences/{exp_soft_delete_2.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_experience_access(self):
        # Attempt delete not found
        response = self.client.delete(f'/experiences/-1/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        exp_not_owned = Experience.objects.create(
            name='owned_by_other_user',
            created_by=Test.followed_user)

        # Attempt to delete someone else's experience
        response = self.client.delete(f'/experiences/{exp_not_owned.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


    def test_playlist_contents(self):
        """
        * Ensures soft deleting happens.
        * A user can only "delete" their own content.
        * Ensures that it looks like the experience was deleted.
        * * Both from querying an Experience by ID and
        * * that the playlist doesn't have it anymore.
        """
        playlist: Playlist = Playlist.objects.create(
            name='test_soft_delete_bl',
            created_by=GlobalTestCredentials.user)

        soft_delete_cat = LifeFrameCategoryOverrides.relevant['categories'][1]
        exp_soft_delete: Experience = Experience.objects.create(
            name='will_soft_delete',
            created_by=GlobalTestCredentials.user,
            categories=[soft_delete_cat.id])

        # Add 3 experiences to the playlist
        experiences_to_add = [
            Test.experience.id,
            Test.experience_from_followed.id,
            exp_soft_delete.id,
        ]
        response = self.client.post(f'/playlists/{playlist.id}/experiences/',
            data={'experiences': experiences_to_add}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Make sure the playlist has 3 experiences
        response = self.client.get(f'/playlists/{playlist.id}/')
        self.assertEqual(response.data['num_experiences'], 3)
        # Make sure the playlist has 3 experiences
        response = self.client.get(f'/playlists/{playlist.id}/experiences/')
        self.assertEqual(len(response.data['results']), 3)

        # Make sure the playlist has the expected aggregated categories
        playlist.refresh_from_db()
        expected_categories = set(
            (Test.experience.categories or []) +
            (Test.experience_from_followed.categories or []) +
            (exp_soft_delete.categories or []))
        self.assertSetEqual(set(playlist.aggregated_categories), expected_categories)

        # Complete 2 experiences
        self.client.post(f'/experiences/{Test.experience.pk}/accept/')
        self.client.post(f'/experiences/{Test.experience.pk}/complete/', data={'minutes_offset': 0})
        self.client.post(f'/experiences/{exp_soft_delete.pk}/accept/')
        self.client.post(f'/experiences/{exp_soft_delete.pk}/complete/', data={'minutes_offset': 0})
        response = self.client.get(f'/playlists/{playlist.id}/')
        self.assertEqual(response.data['num_completed_experiences'], 2)

        # Soft delete golden path
        self.assertIsNone(exp_soft_delete.deleted_at)
        response = self.client.delete(f'/experiences/{exp_soft_delete.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        exp_soft_delete.refresh_from_db()
        playlist.refresh_from_db()

        # item still exists in playlist but is marked as deleted
        self.assertEqual(playlist.experiences.count(), 2)

        # Make sure the playlist doesn't have the soft deleted
        # experience in the count
        response = self.client.get(f'/playlists/{playlist.id}/')
        self.assertEqual(response.data['num_experiences'], 2)
        self.assertEqual(response.data['num_completed_experiences'], 1)

        # Make sure the playlist has 1 less experience
        response = self.client.get(f'/playlists/{playlist.id}/experiences/')
        self.assertEqual(len(response.data['results']), 2)

        # Make sure the aggregated categories no longer contains
        # the soft-deleted experience's category
        expected_categories = set(
            (Test.experience.categories or []) +
            (Test.experience_from_followed.categories or []))
        self.assertSetEqual(set(playlist.aggregated_categories), expected_categories)


    def test_follow_feed(self):
        # Follow feed experience counts are correct after deleting one
        url = '/follow_feed/'
        response = self.client.get(url)
        self.assertEqual(len(response.data['experiences']), 2)

        Test.experience_from_followed.delete()

        response = self.client.get(url)
        self.assertEqual(len(response.data['experiences']), 1)


    def test_user_profile_feed(self):
        # Profile feed experience counts are correct after deleting one
        url = f'/users/{GlobalTestCredentials.user.id}/profile_feed/?experiences=true'
        response = self.client.get(url)
        self.assertEqual(len(response.data['results']), 1)

        Test.experience.delete()

        response = self.client.get(url + '&debug=true')
        self.assertEqual(len(response.data['results']), 0)


    def test_discover_feed(self):
        # Discover feed experience counts are correct after deleting one
        url = '/discover_feed/'
        response = self.client.get(url, {
            # Test experiences don't have images
            'with_images': 'false',
        })
        self.assertEqual(len(response.data['experiences']), 1)

        Test.experience_from_followed.delete()

        response = self.client.get(url, {
            'with_images': 'false',
        })
        self.assertEqual(len(response.data['experiences']), 0)


    def test_discover_search(self):
        # Discover search experience counts are correct after deleting one
        url = f'/discover_feed/search/?phrase={Test.experience_from_followed.name}'
        response = self.client.get(url)
        found_count = 0
        result: dict
        for result in response.data:
            if result['name'] == Test.experience_from_followed.name:
                found_count += 1
        self.assertEqual(found_count, 1)

        Test.experience_from_followed.delete()

        response = self.client.get(url)
        found_count = 0
        result: dict
        for result in response.data:
            if result['name'] == Test.experience_from_followed.name:
                found_count += 1
        self.assertEqual(found_count, 0)


    def test_action_page(self):
        global_user: User = GlobalTestCredentials.user
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        url = f'/action/content_counts/'

        # Test initially created content from this class
        response = self.client.get(url)
        expectations = {
            # Accepted Count
            'experience_count': 0,
            # Accepted and not completed count
            'active_experience_count': 0,
            # Completed count
            'completed_playlist_count': 0,
            # Total post count
            'post_count': 0,
            # roughly:
            # user.saved_experiences.count() + user.saved_playlists.count()
            'saved_for_later_count': 0,
            # Any Exp that has an ending time that's within a week
            'upcoming_experience_count': 0,
            # Any BL that has an ending time that's within a week
            'upcoming_playlist_count': 0,
        }
        for key in expectations:
            self.assertEqual(
                response.data[key],
                expectations[key],
                msg=self.color_yellow(f'key: {key}'))


        # global user accepts and saves an experience they created
        ExperienceAccept.objects.create(
            user=global_user,
            experience=Test.experience)
        ExperienceSave.objects.create(
            user=global_user,
            experience=Test.experience)

        # global user accepts and saves an experience from a user they follow
        ExperienceAccept.objects.create(
            user=global_user,
            experience=Test.experience_from_followed)
        ExperienceSave.objects.create(
            user=global_user,
            experience=Test.experience_from_followed)

        # global user creates an experience that has an end time in the future and accepts it
        another_experience: Experience = Experience.objects.create(
            created_by=global_user,
            name='Another owned experience',
            end_time=now + datetime.timedelta(hours=6))
        ExperienceAccept.objects.create(
            user=global_user,
            experience=another_experience)

        response = self.client.get(url)
        expectations = {
            'experience_count': 3,
            'active_experience_count': 3,
            'saved_for_later_count': 2,
            'upcoming_experience_count': 1,
        }
        for key in expectations:
            self.assertEqual(
                response.data[key],
                expectations[key],
                msg=self.color_yellow(f'key: {key}'))

        # Delete an experience
        Test.experience.delete()
        response = self.client.get(url)
        expectations = {
            'experience_count': 2,
            'active_experience_count': 2,
            'saved_for_later_count': 1,
            # This should not change, the upcoming was from the
            # creation of `another_experience`
            'upcoming_experience_count': 1,
        }
        for key in expectations:
            self.assertEqual(
                response.data[key],
                expectations[key],
                msg=self.color_yellow(f'key: {key}'))

        # Delete another experience
        another_experience.delete()
        response = self.client.get(url)
        expectations = {
            'experience_count': 1,
            'active_experience_count': 1,
            'saved_for_later_count': 1,
            'upcoming_experience_count': 0,
        }
        for key in expectations:
            self.assertEqual(
                response.data[key],
                expectations[key],
                msg=self.color_yellow(f'key: {key}'))

        # delete another experience
        Test.experience_from_followed.delete()
        response = self.client.get(url)
        expectations = {
            'experience_count': 0,
            'active_experience_count': 0,
            'saved_for_later_count': 0,
            'upcoming_experience_count': 0,
        }
        for key in expectations:
            self.assertEqual(
                response.data[key],
                expectations[key],
                msg=self.color_yellow(f'key: {key}'))

    def color_yellow(self, text: str):
        color = colorama.Fore.LIGHTYELLOW_EX
        reset = colorama.Style.RESET_ALL
        return f'{color}{text}{reset}'
