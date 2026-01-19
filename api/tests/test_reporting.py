from . import SilenceableAPITestCase
from rest_framework.authtoken.models import Token
from rest_framework import status

from api.enums import ReportType
from api.models import (
    Playlist,
    Experience,
    Post,
    Comment,
    User,
)

class Test(SilenceableAPITestCase):
    sender: User
    offender: User
    sender_token: Token
    experience: Experience
    playlist: Playlist
    post: Post
    comment: Comment
    sender_comment: Comment

    # Ran before all tests only once.
    def setUpTestData():
        Test.sender =            User.objects.create(
            username='u_1',
            email='sender@email.com',
            email_verified=True)
        Test.offender =          User.objects.create(
            username='u_2',
            email='offender@email.com',
            email_verified=True)
        Test.sender_token =     Token.objects.create(
            user=Test.sender)

        sender = Test.sender
        offender = Test.offender
        Test.experience =     Experience.objects.create(created_by=offender, name='a', description='b')
        Test.playlist =       Playlist.objects.create(created_by=offender, name='c')
        Test.post =           Post.objects.create(created_by=offender, text='d', experience=Test.experience)
        Test.comment =        Comment.objects.create(created_by=offender, text='e', post=Test.post)
        Test.sender_comment = Comment.objects.create(created_by=sender,   text='f', post=Test.post)


    # Ran before each test.
    def setUp(self):
        super().setUp()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {Test.sender_token}')


    def test_required_params_fail(self):
        offender = Test.offender.id
        post = Test.post.id
        data: list[dict] = [
            # No key => value pairs
            {},
            # No offender
            { 'type': None },
            { 'type': ReportType.SPAM.value },
            # No type
            { 'offender': None },
            { 'offender': offender },
            # Keys provided but with Nones
            { 'offender': None,     'type': None },
            { 'offender': None,     'type': ReportType.SPAM.value },
            { 'offender': offender, 'type': None },
            # type OTHER with no details
            { 'offender': offender, 'type': ReportType.OTHER.value                                },
            { 'offender': offender, 'type': ReportType.OTHER.value,                  'post': post },
            { 'offender': offender, 'type': ReportType.OTHER.value, 'details': None,              },
            { 'offender': offender, 'type': ReportType.OTHER.value, 'details': None, 'post': post },
        ]
        for data_dict in data:
            response = self.client.post('/reports/', data=data_dict, format='json')
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


    def test_unknown_type_fail(self):
        offender = Test.offender.id
        post = Test.post.id
        data: list[dict] = [
            { 'offender': offender, 'type': -1,                               },
            { 'offender': offender, 'type': -1,                  'post': post },
            { 'offender': offender, 'type': -1, 'details': None,              },
            { 'offender': offender, 'type': -1, 'details': None, 'post': post },
            { 'offender': offender, 'type': -1, 'details': 'd',               },
            { 'offender': offender, 'type': -1, 'details': 'd',  'post': post },
        ]
        for data_dict in data:
            response = self.client.post('/reports/', data=data_dict, format='json')
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


    def test_more_than_one_contents_fail(self):
        offender_id = Test.offender.id
        playlist_id = Test.playlist.id
        experience_id = Test.experience.id
        post_id = Test.post.id
        comment_id = Test.comment.id
        report_type = ReportType.SPAM.value
        # Will add the offender and type after.
        data = [
            {
                'playlist': playlist_id,
                'experience': experience_id,
                'post': post_id,
                'comment': comment_id,
            },
            {
                # 'playlist': playlist_id,
                'experience': experience_id,
                'post': post_id,
                'comment': comment_id,
            },
            {
                'playlist': playlist_id,
                # 'experience': experience_id,
                'post': post_id,
                'comment': comment_id,
            },
            {
                'playlist': playlist_id,
                'experience': experience_id,
                # 'post': post_id,
                'comment': comment_id,
            },
            {
                'playlist': playlist_id,
                'experience': experience_id,
                'post': post_id,
                # 'comment': comment_id,
            },
            {
                # 'playlist': playlist_id,
                # 'experience': experience_id,
                'post': post_id,
                'comment': comment_id,
            },
            {
                # 'playlist': playlist_id,
                'experience': experience_id,
                # 'post': post_id,
                'comment': comment_id,
            },
            {
                # 'playlist': playlist_id,
                'experience': experience_id,
                'post': post_id,
                # 'comment': comment_id,
            },
            {
                'playlist': playlist_id,
                # 'experience': experience_id,
                # 'post': post_id,
                'comment': comment_id,
            },
            {
                'playlist': playlist_id,
                # 'experience': experience_id,
                'post': post_id,
                # 'comment': comment_id,
            },
            {
                'playlist': playlist_id,
                'experience': experience_id,
                # 'post': post_id,
                # 'comment': comment_id,
            },
        ]
        for data_dict in data:
            data_dict['offender'] = offender_id
            data_dict['type'] = report_type
            response = self.client.post('/reports/', data=data_dict, format='json')
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


    def test_report_on_offender_all_success(self):
        offender = Test.offender.id
        pass_data: list[dict] = [
            {
                'offender': offender,
                'type': ReportType.ABUSIVE_CONTENT.value,
                'details': None,
            },
            {
                'offender': offender,
                'type': ReportType.OTHER.value,
                'details': 'Some other reason',
            },
        ]
        for data_dict in pass_data:
            response = self.client.post('/reports/', data=data_dict, format='json')
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)


    def test_user_reports_themself_as_offender(self):
        sender = Test.sender.id
        sender_comment = Test.sender_comment.id
        data_dict = {
            'offender': sender,
            'type': ReportType.SPAM.value,
            'details': 'I am reporting myself for spam',
        }
        response = self.client.post('/reports/', data=data_dict, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data_dict = {
            'offender': sender,
            'type': ReportType.SPAM.value,
            'details': 'I am reporting my own comment for spam',
            'comment': sender_comment,
        }
        response = self.client.post('/reports/', data=data_dict, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


    def test_create_report_on_all_types(self):
        offender_id = Test.offender.id
        playlist_id = Test.playlist.id
        experience_id = Test.experience.id
        post_id = Test.post.id
        comment_id = Test.comment.id
        data: list[dict] = []
        for report_type in ReportType.values:
            data += [
                {
                    'offender': offender_id,
                    'type': report_type,
                    'details': 'User was bad',
                },
                {
                    'offender': offender_id,
                    'type': report_type,
                    'details': 'Playlist was bad',
                    'playlist': playlist_id,
                },
                {
                    'offender': offender_id,
                    'type': report_type,
                    'details': 'Experience was bad',
                    'experience': experience_id,
                },
                {
                    'offender': offender_id,
                    'type': report_type,
                    'details': 'Post was bad',
                    'post': post_id,
                },
                {
                    'offender': offender_id,
                    'type': report_type,
                    'details': 'Comment was bad',
                    'comment': comment_id,
                },
            ]
        for data_dict in data:
            response = self.client.post('/reports/', data=data_dict, format='json')
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
