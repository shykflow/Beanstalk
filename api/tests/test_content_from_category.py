from rest_framework import status

from api.models import (
    CustomCategory,
    Experience,
    ExperienceCostRating,
    ExperienceStarRating,
    Playlist,
    PlaylistCostRating,
    PlaylistStarRating,
)
from api.testing_overrides import GlobalTestCredentials
from . import disable_logging, SilenceableAPITestCase

class Test(SilenceableAPITestCase):

    custom_category: CustomCategory

    def setUpTestData():
        Test.custom_category = CustomCategory.objects.create(
            name='test_category_name')


    def setUp(self):
        super().setUp()
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {GlobalTestCredentials.token}')


    def test_allowed_params(self):
        endpoint_starts = (
            '/category/content_from_category_id/?id=1',
            '/category/content_from_custom_category/' \
                f'?name={Test.custom_category.name}',
            # Name is always required for now, even when providing the id.
            # This is expected behavior. This is because the Flutter app was
            # built by treating the name like a primary key and the project is
            # not ready to swap over to ids only.
            # If the id is provided the name is ignored on this endpoint.
            '/category/content_from_custom_category/' \
                f'?name={Test.custom_category.name}' \
                f'&id={Test.custom_category.id}',
        )
        content_types = [
            'experiences',
            'playlists',
            'users',
            'all',
        ]
        # List of (param, value, should_pass),
        param_pairs = (
            # Any search is fine
            ('search', 'asdf', True),
            # Empty search is ignored
            ('search', '', True),
            ('search', None, True),
            ('cost', '-1', False),
            ('cost', '0', True),
            ('cost', '1', True),
            ('cost', '2', True),
            ('cost', '3', True),
            ('cost', '4', True),
            ('cost', '5', False),
            ('stars', '0', False),
            ('stars', '1', True),
            ('stars', '2', True),
            ('stars', '3', True),
            ('stars', '4', True),
            ('stars', '5', True),
            ('stars', '6', False),
        )
        iteration = 0
        for endpoint_start in endpoint_starts:
            for content_type in content_types:
                for param_pair in param_pairs:
                    iteration += 1
                    param = param_pair[0]
                    value = param_pair[1]
                    should_200 = param_pair[2]
                    failed_assertion_msg = '\n' \
                        f'    iteration:      {iteration}\n' \
                        f'    endpoint_start: {endpoint_start}\n' \
                        f'    content_type:   {content_type}\n' \
                        f'    param:          {param}\n' \
                        f'    value:          {value}\n' \
                        f'    should_200:     {should_200}'
                    url = ''.join([
                        endpoint_start,
                        f'&content_type={content_type}'
                        f'&{param}={value}',
                        #! BACK COMPAT (EARLIEST_SUPPORTED_APP_VERSION=15)
                        '&version=2',
                        #! END BACK COMPAT
                        #! (don't need to set v2 after everyone updates to version 15 and we delete version 1)
                    ])
                    response = self.client.get(url)
                    if should_200:
                        self.assertEqual(
                            response.status_code,
                            status.HTTP_200_OK,
                            msg=failed_assertion_msg)
                    else:
                        self.assertEqual(
                            response.status_code,
                            status.HTTP_400_BAD_REQUEST,
                            msg=failed_assertion_msg)

    def test_shape_content_from_category_id(self):
        content_types = [
            'experiences',
            'playlists',
            'users',
            'all',
        ]
        for content_type in content_types:
            endpoint = ''.join([
                '/category/content_from_category_id/'
                '?id=1',
                f'&content_type={content_type}'
                #! BACK COMPAT (EARLIEST_SUPPORTED_APP_VERSION=15)
                '&version=2',
                #! END BACK COMPAT
                #! (don't need to set v2 after everyone updates to version 15 and we delete version 1)
            ])
            response = self.client.get(endpoint)
            self.assertEqual(response.status_code, 200)
            response_data = response.data
            self.assertIn('continuation', response_data)
            if content_type == 'all':
                self.assertIsNone(response_data['continuation'])
            else:
                self.assertIsNotNone(response_data['continuation'])
            self.assertIn('experiences', response_data)
            self.assertIn('experience_count', response_data)
            self.assertIn('users', response_data)
            self.assertIn('user_count', response_data)
            self.assertIn('playlists', response_data)
            self.assertIn('playlist_count', response_data)


    def test_shape_content_from_custom_category(self):
        content_types = [
            'experiences',
            'playlists',
            'users',
            'all',
        ]
        for content_type in content_types:
            endpoint = ''.join([
                '/category/content_from_custom_category/'
                f'?name={Test.custom_category.name}',
                f'&content_type={content_type}'
                #! BACK COMPAT (EARLIEST_SUPPORTED_APP_VERSION=15)
                '&version=2',
                #! END BACK COMPAT
                #! (don't need to set v2 after everyone updates to version 15 and we delete version 1)
            ])
            response = self.client.get(endpoint)
            self.assertEqual(response.status_code, 200)
            response_data = response.data
            self.assertIn('continuation', response_data)
            if content_type == 'all':
                self.assertIsNone(response_data['continuation'])
            else:
                self.assertIsNotNone(response_data['continuation'])
            self.assertIn('experiences', response_data)
            self.assertIn('experience_count', response_data)
            self.assertIn('users', response_data)
            self.assertIn('user_count', response_data)
            self.assertIn('playlists', response_data)
            self.assertIn('playlist_count', response_data)


    def test_invalid_params_content_from_category_id(self):
        bad_query_params: list[dict[str: str]] = [
            # missing id and content_type
            {},
            # missing content_type
            {'id': '1'},
            # missing id
            {'content_type': 'all'},
            # invalid id and content_type
            {'id': 'abc', 'content_type': 'asdf'},
            # invalid id
            {'id': 'abc', 'content_type': 'all'},
            # invalid content_type
            {'id': '1', 'content_type': 'asdf'},
        ]
        for qps in bad_query_params:
            #! BACK COMPAT (EARLIEST_SUPPORTED_APP_VERSION=15)
            qps['version'] = '2'
            #! END BACK COMPAT
            # ! (don't need to set v2 after everyone updates to version 15 and we delete version 1)
            endpoint = '/category/content_from_category_id/'
            i = 0
            for key, value in qps.items():
                endpoint += '?' if i == 0 else '&'
                endpoint += f'{key}={value}'
                i += 1
            response = self.client.get(endpoint)
            self.assertEqual(response.status_code, 400, msg=endpoint)


    def test_invalid_params_content_from_custom_category(self):
        bad_query_params: list[dict[str: str]] = [
            # missing name and content_type
            {},
            # missing content_type
            {'name': 'abc'},
            # missing name
            {'content_type': 'all' },
            # invalid content_type
            {'name': 'abc', 'content_type': 'asdf'},
        ]
        for qps in bad_query_params:
            #! BACK COMPAT (EARLIEST_SUPPORTED_APP_VERSION=15)
            qps['version'] = '2'
            #! END BACK COMPAT
            #! (don't need to set v2 after everyone updates to version 15 and we delete version 1)
            endpoint = '/category/content_from_custom_category/'
            i = 0
            for key, value in qps.items():
                endpoint += '?' if i == 0 else '&'
                endpoint += f'{key}={value}'
                i += 1
            response = self.client.get(endpoint)
            self.assertEqual(response.status_code, 400, msg=endpoint)


    def test_get_content_from_category_id(self):
        playlist: Playlist = Playlist.objects.create(
            name='playlist',
            created_by=GlobalTestCredentials.user)
        experience: Experience = Experience.objects.create(
            name='experience',
            created_by=GlobalTestCredentials.user,
            categories=[1])
        playlist.experiences.add(experience)
        playlist.update_aggregated_categories()
        content_types = [
            'experiences',
            'playlists',
            'users',
            'all',
        ]
        for content_type in content_types:
            endpoint = ''.join([
                '/category/content_from_category_id/'
                '?id=1',
                f'&content_type={content_type}'
                #! BACK COMPAT (EARLIEST_SUPPORTED_APP_VERSION=15)
                '&version=2',
                #! END BACK COMPAT
                #! (don't need to set v2 after everyone updates to version 15 and we delete version 1)
            ])
            response = self.client.get(endpoint)
            self.assertEqual(response.status_code, 200)
            response_data = response.data
            match (content_type):
                case 'experiences':
                    self.assertEqual(len(response_data['experiences']), 1)
                    self.assertEqual(len(response_data['playlists']), 0)
                    self.assertEqual(len(response_data['users']), 0)
                    self.assertEqual(response_data['experience_count'], 1)
                    self.assertEqual(response_data['playlist_count'], 0)
                    self.assertEqual(response_data['user_count'], 0)
                case 'playlists':
                    self.assertEqual(len(response_data['experiences']), 0)
                    self.assertEqual(len(response_data['playlists']), 1)
                    self.assertEqual(len(response_data['users']), 0)
                    self.assertEqual(response_data['experience_count'], 0)
                    self.assertEqual(response_data['playlist_count'], 1)
                    self.assertEqual(response_data['user_count'], 0)
                case 'users':
                    self.assertEqual(len(response_data['experiences']), 0)
                    self.assertEqual(len(response_data['playlists']), 0)
                    # self.assertEqual(len(response_data['users']), 1)
                    self.assertEqual(response_data['experience_count'], 0)
                    self.assertEqual(response_data['playlist_count'], 0)
                    # self.assertEqual(response_data['user_count'], 1)
                case 'all':
                    self.assertEqual(len(response_data['experiences']), 1)
                    self.assertEqual(len(response_data['playlists']), 1)
                    # self.assertEqual(len(response_data['users']), 1)
                    self.assertEqual(response_data['experience_count'], 1)
                    self.assertEqual(response_data['playlist_count'], 1)
                    # self.assertEqual(response_data['user_count'], 1)


    def test_get_content_from_custom_category(self):
        playlist: Playlist = Playlist.objects.create(
            name='playlist',
            created_by=GlobalTestCredentials.user)
        experience: Experience = Experience.objects.create(
            name='experience',
            created_by=GlobalTestCredentials.user,
            categories=[1])
        playlist.experiences.add(experience)
        playlist.update_aggregated_categories()
        experience.custom_categories.add(Test.custom_category)
        content_types = [
            'experiences',
            'playlists',
            'users',
            'all',
        ]
        for content_type in content_types:
            endpoint = ''.join([
                '/category/content_from_custom_category/'
                f'?name={Test.custom_category.name}',
                f'&content_type={content_type}'
                #! BACK COMPAT (EARLIEST_SUPPORTED_APP_VERSION=15)
                '&version=2',
                #! END BACK COMPAT
                #! (don't need to set v2 after everyone updates to version 15 and we delete version 1)
            ])
            response = self.client.get(endpoint)
            self.assertEqual(response.status_code, 200)
            response_data = response.data
            match (content_type):
                case 'experiences':
                    self.assertEqual(len(response_data['experiences']), 1)
                    self.assertEqual(len(response_data['playlists']), 0)
                    self.assertEqual(len(response_data['users']), 0)
                    self.assertEqual(response_data['experience_count'], 1)
                    self.assertEqual(response_data['playlist_count'], 0)
                    self.assertEqual(response_data['user_count'], 0)
                case 'playlists':
                    self.assertEqual(len(response_data['experiences']), 0)
                    self.assertEqual(len(response_data['playlists']), 1)
                    self.assertEqual(len(response_data['users']), 0)
                    self.assertEqual(response_data['experience_count'], 0)
                    self.assertEqual(response_data['playlist_count'], 1)
                    self.assertEqual(response_data['user_count'], 0)
                case 'users':
                    self.assertEqual(len(response_data['experiences']), 0)
                    self.assertEqual(len(response_data['playlists']), 0)
                    # self.assertEqual(len(response_data['users']), 1)
                    self.assertEqual(response_data['experience_count'], 0)
                    self.assertEqual(response_data['playlist_count'], 0)
                    # self.assertEqual(response_data['user_count'], 1)
                case 'all':
                    self.assertEqual(len(response_data['experiences']), 1)
                    self.assertEqual(len(response_data['playlists']), 1)
                    # self.assertEqual(len(response_data['users']), 1)
                    self.assertEqual(response_data['experience_count'], 1)
                    self.assertEqual(response_data['playlist_count'], 1)
                    # self.assertEqual(response_data['user_count'], 1)


    def test_experience_filter_on_cost_and_stars(self):
        """
        This test relies on how costs can be from 0 to 4 and stars can be from 1 to 5,
        it will use an iterator "i" and "i+1" to do some tests in parallel
        """
        content_types = [
            'experiences',
            'all',
        ]
        category_id = 1
        experiences: list[Experience] = [
            Experience.objects.create(
                name=str(i),
                categories=[category_id],
                created_by=GlobalTestCredentials.user)
            for i in range(5)
        ]
        for i in range(len(experiences)):
            experience = experiences[i]
            ExperienceCostRating.objects.create(
                experience=experience,
                rating=i,
                created_by=GlobalTestCredentials.user)
            ExperienceStarRating.objects.create(
                experience=experience,
                rating=i+1,
                created_by=GlobalTestCredentials.user)
            experience.custom_categories.add(Test.custom_category)
        endpoint_starts = (
            f'/category/content_from_category_id/?id={category_id}',
            '/category/content_from_custom_category/' \
                f'?name={Test.custom_category.name}',
            # Name is always required for now, even when providing the id.
            # This is expected behavior. This is because the Flutter app was
            # built by treating the name like a primary key and the project is
            # not ready to swap over to ids only.
            # If the id is provided the name is ignored on this endpoint.
            '/category/content_from_custom_category/' \
                f'?name={Test.custom_category.name}' \
                f'&id={Test.custom_category.id}',
        )
        iteration = 0
        for i in range(len(experiences)):
            experience = experiences[i]
            for endpoint_start in endpoint_starts:
                for content_type in content_types:
                    iteration += 1

                    # Cost
                    failed_assertion_msg = '\n' \
                        f'    iteration:      {iteration}\n' \
                        f'    endpoint_start: {endpoint_start}\n' \
                        f'    content_type:   {content_type}\n' \
                        f'    cost:           {i}'
                    url = ''.join([
                        endpoint_start,
                        f'&content_type={content_type}'
                        f'&cost={i}',
                        #! BACK COMPAT (EARLIEST_SUPPORTED_APP_VERSION=15)
                        '&version=2',
                        #! END BACK COMPAT
                        #! (don't need to set v2 after everyone updates to version 15 and we delete version 1)
                    ])
                    response = self.client.get(url)
                    experience_dicts = response.data['experiences']
                    correct_exp_dicts = [
                        exp_dict
                        for exp_dict in experience_dicts
                        if exp_dict['average_cost_rating'] <= i
                    ]
                    self.assertTrue(
                        len(correct_exp_dicts) > 0,
                        msg=failed_assertion_msg)

                    # Stars
                    failed_assertion_msg = '\n' \
                        f'    iteration:      {iteration}\n' \
                        f'    endpoint_start: {endpoint_start}\n' \
                        f'    content_type:   {content_type}\n' \
                        f'    stars:          {i+1}'
                    url = ''.join([
                        endpoint_start,
                        f'&content_type={content_type}'
                        f'&stars={i+1}',
                        #! BACK COMPAT (EARLIEST_SUPPORTED_APP_VERSION=15)
                        '&version=2',
                        #! END BACK COMPAT
                        #! (don't need to set v2 after everyone updates to version 15 and we delete version 1)
                    ])
                    response = self.client.get(url)
                    experience_dicts = response.data['experiences']
                    correct_exp_dicts = [
                        exp_dict
                        for exp_dict in experience_dicts
                        if exp_dict['average_star_rating'] >= i+1
                    ]
                    self.assertTrue(
                        len(correct_exp_dicts) > 0,
                        msg=failed_assertion_msg)


    def test_playlist_filter_on_cost_and_stars(self):
        """
        This test relies on how costs can be from 0 to 4 and stars can be from 1 to 5,
        it will use an iterator "i" and "i+1" to do some tests in parallel
        """
        content_types = [
            'playlists',
            'all',
        ]
        category_id = 1
        playlists: list[Playlist] = [
            Playlist.objects.create(
                name=str(i),
                aggregated_categories=[category_id],
                created_by=GlobalTestCredentials.user)
            for i in range(5)
        ]
        playlist_exp: Experience = Experience.objects.create(
            name=f'playlist_exp',
            categories=[category_id],
            created_by=GlobalTestCredentials.user)
        playlist_exp.custom_categories.add(Test.custom_category)
        for i in range(len(playlists)):
            playlist = playlists[i]
            playlist.experiences.add(playlist_exp)
            PlaylistCostRating.objects.create(
                playlist=playlist,
                rating=i,
                created_by=GlobalTestCredentials.user)
            PlaylistStarRating.objects.create(
                playlist=playlist,
                rating=i+1,
                created_by=GlobalTestCredentials.user)
        endpoint_starts = (
            f'/category/content_from_category_id/?id={category_id}',
            '/category/content_from_custom_category/' \
                f'?name={Test.custom_category.name}',
            # Name is always required for now, even when providing the id.
            # This is expected behavior. This is because the Flutter app was
            # built by treating the name like a primary key and the project is
            # not ready to swap over to ids only.
            # If the id is provided the name is ignored on this endpoint.
            '/category/content_from_custom_category/' \
                f'?name={Test.custom_category.name}' \
                f'&id={Test.custom_category.id}',
        )
        iteration = 0
        for i in range(len(playlists)):
            playlist = playlists[i]
            for endpoint_start in endpoint_starts:
                for content_type in content_types:
                    iteration += 1

                    # Cost
                    failed_assertion_msg = '\n' \
                        f'    iteration:      {iteration}\n' \
                        f'    endpoint_start: {endpoint_start}\n' \
                        f'    content_type:   {content_type}\n' \
                        f'    cost:           {i}'
                    url = ''.join([
                        endpoint_start,
                        f'&content_type={content_type}'
                        f'&cost={i}',
                        #! BACK COMPAT (EARLIEST_SUPPORTED_APP_VERSION=15)
                        '&version=2',
                        #! END BACK COMPAT
                        #! (don't need to set v2 after everyone updates to version 15 and we delete version 1)
                    ])
                    response = self.client.get(url)
                    playlist_dicts = response.data['playlists']
                    correct_pl_dicts = [
                        pl_dict
                        for pl_dict in playlist_dicts
                        if pl_dict['average_cost_rating'] <= i
                    ]
                    self.assertTrue(
                        len(correct_pl_dicts) > 0,
                        msg=failed_assertion_msg)

                    # Stars
                    failed_assertion_msg = '\n' \
                        f'    iteration:      {iteration}\n' \
                        f'    endpoint_start: {endpoint_start}\n' \
                        f'    content_type:   {content_type}\n' \
                        f'    stars:          {i+1}'
                    url = ''.join([
                        endpoint_start,
                        f'&content_type={content_type}'
                        f'&stars={i+1}',
                        #! BACK COMPAT (EARLIEST_SUPPORTED_APP_VERSION=15)
                        '&version=2',
                        #! END BACK COMPAT
                        #! (don't need to set v2 after everyone updates to version 15 and we delete version 1)
                    ])
                    response = self.client.get(url)
                    playlist_dicts = response.data['playlists']
                    correct_pl_dicts = [
                        pl_dict
                        for pl_dict in playlist_dicts
                        if pl_dict['average_star_rating'] >= i+1
                    ]
                    self.assertTrue(
                        len(correct_pl_dicts) > 0,
                        msg=failed_assertion_msg)
