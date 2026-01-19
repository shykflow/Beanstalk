import json
from rest_framework import status
from django.conf import settings
from django.db.models import Model

from api.enums import AttachmentType
from api.models import (
    Attachment,
    Playlist,
    Experience,
    Post
)
from api.testing_overrides import GlobalTestCredentials, TestFiles
from . import SilenceableAPITestCase


class Test(SilenceableAPITestCase):

    experience: Experience
    post: Post
    playlist: Playlist

    def setUpTestData():
        Test.experience = Experience.objects.create(
            name="a",
            description="aa",
            created_by=GlobalTestCredentials.user)
        Test.post = Post.objects.create(
            name="b",
            text="bb",
            created_by=GlobalTestCredentials.user)
        Test.playlist = Playlist.objects.create(
            name="c",
            description="cc",
            created_by=GlobalTestCredentials.user)

    def setUp(self):
        super().setUp()
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {GlobalTestCredentials.token}')


    def test_all_steps_single_attachment(self):
        resources = {
            'posts': Test.post,
            'experiences': Test.experience,
            'playlists': Test.playlist,
        }
        for resource_key in resources:
            resource_instance = resources[resource_key]
            # Create
            name = 'Name'
            description = 'Description'
            sequence = 0
            data = {
                'file-key': TestFiles.get_simple_uploaded_file('jpg'),
                'thumbnail-key': TestFiles.get_simple_uploaded_file('jpg'),
                'json': json.dumps({
                    'create': [
                        {
                            'file_key': 'file-key',
                            'thumbnail_key': 'thumbnail-key',
                            'name': name,
                            'description': description,
                            'sequence': sequence,
                        },
                    ],
                    'update': [],
                    'delete': [],
                }),
            }
            response = self.client.post(
                path=f'/{resource_key}/{resource_instance.pk}/attachments/',
                data=data)
            self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
            self.assertEqual(len(response.data['created']), 1)
            self.assertEqual(len(response.data['updated']), 0)
            self.assertEqual(len(response.data['deleted']), 0)
            created_dict = response.data['created'][0]
            self.assertEqual(created_dict['name'], name)
            self.assertEqual(created_dict['description'], description)
            self.assertEqual(created_dict['sequence'], sequence)
            self.assertIsNotNone(created_dict['file'])
            self.assertIsNotNone(created_dict['thumbnail'])
            self.assertIsNotNone(created_dict['type'])
            self.assertEqual(created_dict['type'], AttachmentType.IMAGE)

            # Verify from db
            attachment_id = created_dict['id']
            attachment: Attachment = Attachment.objects.filter(pk=attachment_id).first()
            self.assertIsNotNone(attachment)
            self.assertEqual(attachment.name, name)
            self.assertEqual(attachment.description, description)

            # GET
            response = self.client.get(f'/{resource_key}/{resource_instance.pk}/attachments/')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(len(response.data), 1)
            get_dict = response.data[0]
            self.assertEqual(get_dict['name'], name)
            self.assertEqual(get_dict['description'], description)
            self.assertEqual(get_dict['sequence'], sequence)
            self.assertIsNotNone(get_dict['file'])
            self.assertIsNotNone(get_dict['thumbnail'])
            self.assertIsNotNone(get_dict['type'])
            self.assertEqual(get_dict['type'], AttachmentType.IMAGE)

            # Update
            name = 'Modified name'
            description = 'Modified description'
            sequence += 1
            data = {
                'json': json.dumps({
                    'create': [],
                    'update': [
                        {
                            'id': attachment_id,
                            'name': name,
                            'description': description,
                            'sequence': sequence,
                        },
                    ],
                    'delete': [],
                }),
            }
            response = self.client.post(
                path=f'/{resource_key}/{resource_instance.pk}/attachments/',
                data=data)
            self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
            self.assertEqual(len(response.data['created']), 0)
            self.assertEqual(len(response.data['updated']), 1)
            self.assertEqual(len(response.data['deleted']), 0)
            updated_dict = response.data['updated'][0]
            self.assertEqual(updated_dict['id'], attachment_id)
            self.assertEqual(updated_dict['name'], name)
            self.assertEqual(updated_dict['description'], description)
            self.assertEqual(updated_dict['sequence'], sequence)
            self.assertIsNotNone(updated_dict['file'])
            self.assertIsNotNone(updated_dict['thumbnail'])
            self.assertIsNotNone(updated_dict['type'])
            self.assertEqual(updated_dict['type'], AttachmentType.IMAGE)

            # GET
            response = self.client.get(f'/{resource_key}/{resource_instance.pk}/attachments/')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(len(response.data), 1)
            get_dict = response.data[0]
            self.assertEqual(get_dict['name'], name)
            self.assertEqual(get_dict['description'], description)
            self.assertEqual(get_dict['sequence'], sequence)
            self.assertIsNotNone(get_dict['file'])
            self.assertIsNotNone(get_dict['thumbnail'])
            self.assertIsNotNone(get_dict['type'])
            self.assertEqual(get_dict['type'], AttachmentType.IMAGE)

            # Delete
            data = {
                'json': json.dumps({
                    'create': [],
                    'update': [],
                    'delete': [attachment_id],
                }),
            }
            response = self.client.post(
                path=f'/{resource_key}/{resource_instance.pk}/attachments/',
                data=data)
            self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
            self.assertEqual(len(response.data['created']), 0)
            self.assertEqual(len(response.data['updated']), 0)
            self.assertEqual(len(response.data['deleted']), 1)
            self.assertEqual(response.data['deleted'][0], attachment_id)

            # GET
            response = self.client.get(f'/{resource_key}/{resource_instance.pk}/attachments/')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(len(response.data), 0)


    def test_bad_file_reference(self):
        resources = {
            'posts': Test.post,
            'experiences': Test.experience,
            'playlists': Test.playlist,
        }
        for resource_key in resources:
            resource_instance: Model = resources[resource_key]
            # Fail - file not attached
            data = {
                'json': json.dumps({
                    'create': [
                        {
                            'file_key': 'file-key-1',
                            'thumbnail_key': 'thumbnail-key-1',
                            'name': None,
                            'description': None,
                            'sequence': 0,
                        },
                    ],
                    'update': [],
                    'delete': [],
                }),
            }
            response = self.client.post(
                path=f'/{resource_key}/{resource_instance.pk}/attachments/',
                data=data)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, msg=resource_key)

            # Fail - names don't match file
            data = {
                'file-key-1': TestFiles.get_simple_uploaded_file('doc'),
                'json': json.dumps({
                    'create': [
                        {
                            'file_key': 'file-key-1111',
                            'name': None,
                            'description': None,
                            'sequence': 0,
                        },
                    ],
                    'update': [],
                    'delete': [],
                }),
            }
            response = self.client.post(
                path=f'/{resource_key}/{resource_instance.pk}/attachments/',
                data=data)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, msg=resource_key)

            # Fail - names don't match thumbnail
            data = {
                'file-key-1': TestFiles.get_simple_uploaded_file('jpg'),
                'thumbnail-key-1': TestFiles.get_simple_uploaded_file('jpg'),
                'json': json.dumps({
                    'create': [
                        {
                            'file_key': 'file-key-1',
                            'thumbnail_key': 'thumbnail-key-1111',
                            'name': None,
                            'description': None,
                            'sequence': 0,
                        },
                    ],
                    'update': [],
                    'delete': [],
                }),
            }
            response = self.client.post(
                path=f'/{resource_key}/{resource_instance.pk}/attachments/',
                data=data)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, msg=resource_key)

            # Fail - names don't match file and thumbnail
            data = {
                'file-key-1': TestFiles.get_simple_uploaded_file('jpg'),
                'thumbnail-key-1': TestFiles.get_simple_uploaded_file('jpg'),
                'json': json.dumps({
                    'create': [
                        {
                            'file_key': 'file-key-1111',
                            'thumbnail_key': 'thumbnail-key-1111',
                            'name': None,
                            'description': None,
                            'sequence': 0,
                        },
                    ],
                    'update': [],
                    'delete': [],
                }),
            }
            response = self.client.post(
                path=f'/{resource_key}/{resource_instance.pk}/attachments/',
                data=data)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, msg=resource_key)


    def test_update_delete_same_attachment(self):
        resources = {
            'posts': Test.post,
            'experiences': Test.experience,
            'playlists': Test.playlist,
        }
        for resource_key in resources:
            resource_instance: Model = resources[resource_key]
            # Create
            data = {
                'file-key-1': TestFiles.get_simple_uploaded_file('jpg'),
                'thumbnail-key-1': TestFiles.get_simple_uploaded_file('jpg'),
                'file-key-2': TestFiles.get_simple_uploaded_file('doc'),
                'json': json.dumps({
                    'create': [
                        {
                            'file_key': 'file-key-1',
                            'thumbnail_key': 'thumbnail-key-1',
                            'name': None,
                            'description': None,
                            'sequence': 0,
                        },
                        {
                            'file_key': 'file-key-2',
                            'name': None,
                            'description': None,
                            'sequence': 1,
                        },
                    ],
                    'update': [],
                    'delete': [],
                }),
            }
            response = self.client.post(
                path=f'/{resource_key}/{resource_instance.pk}/attachments/',
                data=data)
            self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED, msg=resource_key)
            self.assertEqual(len(response.data['created']), 2, msg=resource_key)
            self.assertEqual(len(response.data['updated']), 0, msg=resource_key)
            self.assertEqual(len(response.data['deleted']), 0, msg=resource_key)
            id_1 = response.data['created'][0]['id']
            id_2 = response.data['created'][1]['id']

            resource_instance.refresh_from_db()
            attachment_count = resource_instance.attachments.count()
            self.assertEqual(attachment_count, 2, msg=resource_key)

            # Create another
            data = {
                'file-key-1': TestFiles.get_simple_uploaded_file('docx'),
                'json': json.dumps({
                    'create': [
                        {
                            'file_key': 'file-key-1',
                            'name': None,
                            'description': None,
                            'sequence': 2,
                        },
                    ],
                    'update': [],
                    'delete': [],
                }),
            }
            response = self.client.post(
                path=f'/{resource_key}/{resource_instance.pk}/attachments/',
                data=data)
            self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED, msg=resource_key)
            self.assertEqual(len(response.data['created']), 1, msg=resource_key)
            self.assertEqual(len(response.data['updated']), 0, msg=resource_key)
            self.assertEqual(len(response.data['deleted']), 0, msg=resource_key)
            id_3 = response.data['created'][0]['id']
            resource_instance.refresh_from_db()
            attachment_count = resource_instance.attachments.count()
            self.assertEqual(attachment_count, 3, msg=resource_key)

            # Update
            data = {
                'json': json.dumps({
                    'create': [],
                    'update': [
                        {
                            'id': id_1,
                            'name': 'new name',
                            'description': 'new description',
                            'sequence': 0,
                        },
                    ],
                    'delete': [],
                }),
            }
            response = self.client.post(
                path=f'/{resource_key}/{resource_instance.pk}/attachments/',
                data=data)
            self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED, msg=resource_key)
            self.assertEqual(len(response.data['created']), 0, msg=resource_key)
            self.assertEqual(len(response.data['updated']), 1, msg=resource_key)
            self.assertEqual(len(response.data['deleted']), 0, msg=resource_key)
            resource_instance.refresh_from_db()
            attachment_count = resource_instance.attachments.count()
            self.assertEqual(attachment_count, 3, msg=resource_key)

            # Delete
            data = {
                'json': json.dumps({
                    'create': [],
                    'update': [],
                    'delete': [id_2],
                }),
            }
            response = self.client.post(
                path=f'/{resource_key}/{resource_instance.pk}/attachments/',
                data=data)
            self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED, msg=resource_key)
            self.assertEqual(len(response.data['created']), 0, msg=resource_key)
            self.assertEqual(len(response.data['updated']), 0, msg=resource_key)
            self.assertEqual(len(response.data['deleted']), 1, msg=resource_key)
            resource_instance.refresh_from_db()
            attachment_count = resource_instance.attachments.count()
            self.assertEqual(attachment_count, 2, msg=resource_key)

            # Fail update because deleted
            data = {
                'json': json.dumps({
                    'create': [],
                    'update': [
                        {
                            'id': id_2,
                            'name': 'new name',
                            'description': 'new description',
                            'sequence': 1,
                        },
                    ],
                    'delete': [],
                }),
            }
            response = self.client.post(
                path=f'/{resource_key}/{resource_instance.pk}/attachments/',
                data=data)
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, msg=resource_key)
            resource_instance.refresh_from_db()
            attachment_count = resource_instance.attachments.count()
            self.assertEqual(attachment_count, 2, msg=resource_key)


    def test_update_delete_same_attachment(self):
        resources = {
            'posts': Test.post,
            'experiences': Test.experience,
            'playlists': Test.playlist,
        }
        for resource_key in resources:
            resource_instance: Model = resources[resource_key]
            # Create
            data = {
                'file-key-1': TestFiles.get_simple_uploaded_file('doc'),
                'json': json.dumps({
                    'create': [
                        {
                            'file_key': 'file-key-1',
                            'name': None,
                            'description': None,
                            'sequence': 0,
                        },
                    ],
                    'update': [],
                    'delete': [],
                }),
            }
            response = self.client.post(
                path=f'/{resource_key}/{resource_instance.pk}/attachments/',
                data=data)
            self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED, msg=resource_key)
            id = response.data['created'][0]['id']

            # Update and delete same
            data = {
                'json': json.dumps({
                    'create': [],
                    'update': [
                        {
                            'id': id,
                            'name': 'new name',
                            'description': 'new description',
                            'sequence': 0,
                        },
                    ],
                    'delete': [id],
                }),
            }
            response = self.client.post(
                path=f'/{resource_key}/{resource_instance.pk}/attachments/',
                data=data)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, msg=resource_key)


    def test_create_each_attachment_file_type(self):
        json_dict = {
            'create': [
                {
                    'file_key': 'file-doc',
                    'name': 'Test doc',
                    'description': 'This is a test doc',
                    'sequence': 0,
                },
                {
                    'file_key': 'file-docx',
                    'name': 'Test docx',
                    'description': 'This is a test docx',
                    'sequence': 1,
                },
                {
                    'file_key': 'file-gif',
                    'name': 'Test gif',
                    'description': 'This is a test gif',
                    'sequence': 2,
                },
                {
                    'file_key': 'file-jpeg',
                    'thumbnail_key': 'file-jpeg-thumbnail',
                    'name': 'Test jpeg',
                    'description': 'This is a test jpeg',
                    'sequence': 3,
                },
                {
                    'file_key': 'file-jpg',
                    'thumbnail_key': 'file-jpg-thumbnail',
                    'name': 'Test jpg',
                    'description': 'This is a test jpg',
                    'sequence': 4,
                },
                {
                    'file_key': 'file-mp3',
                    'name': 'Test mp3',
                    'description': 'This is a test mp3',
                    'sequence': 5,
                },{
                    'file_key': 'file-mp4',
                    'name': 'Test video',
                    'description': 'This is a test video',
                    'sequence': 6,
                },
                {
                    'file_key': 'file-pdf',
                    'name': 'Test pdf',
                    'description': 'This is a test pdf',
                    'sequence': 7,
                },
                {
                    'file_key': 'file-png',
                    'thumbnail_key': 'file-png-thumbnail',
                    'name': 'Test png',
                    'description': 'This is a test png',
                    'sequence': 8,
                },
                {
                    'file_key': 'file-txt',
                    'name': 'Test txt',
                    'description': 'This is a test txt',
                    'sequence': 9,
                },
            ],
        }
        sequences_with_thumbnails = [
            d['sequence']
            for d in json_dict['create']
            if d.get('thumbnail_key') is not None
        ]
        data = {
            f'file-doc': TestFiles.get_simple_uploaded_file('doc'),
            f'file-docx': TestFiles.get_simple_uploaded_file('docx'),
            f'file-gif': TestFiles.get_simple_uploaded_file('gif'),
            f'file-jpeg': TestFiles.get_simple_uploaded_file('jpeg'),
            f'file-jpeg-thumbnail': TestFiles.get_simple_uploaded_file('jpeg'),
            f'file-jpg': TestFiles.get_simple_uploaded_file('jpg'),
            f'file-jpg-thumbnail': TestFiles.get_simple_uploaded_file('jpg'),
            f'file-mp3': TestFiles.get_simple_uploaded_file('mp3'),
            f'file-mp4': TestFiles.get_simple_uploaded_file('mp4'),
            f'file-pdf': TestFiles.get_simple_uploaded_file('pdf'),
            f'file-png': TestFiles.get_simple_uploaded_file('png'),
            f'file-png-thumbnail': TestFiles.get_simple_uploaded_file('jpg'),
            f'file-txt': TestFiles.get_simple_uploaded_file('txt'),
            'json': json.dumps(json_dict),
        }
        response = self.client.post(
            path=f'/posts/{Test.post.pk}/attachments/',
            data=data)
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

        response = self.client.get(path=f'/posts/{Test.post.pk}/attachments/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        for data in response.data:
            msg = f"Attachment with name `{data['name']}` did not have an file returned"
            self.assertIsNotNone(data['file'], msg=msg)
            if data['sequence'] in sequences_with_thumbnails:
                thumbnail: str = data['thumbnail']
                msg = f"Attachment with name `{data['name']}` did not have an thumbnail returned"
                self.assertIsNotNone(thumbnail, msg=msg)
                self.assertNotEqual(thumbnail.strip(), '', msg=msg)


    def test_create_too_many_attachments(self):
        # Create the max number of attachments
        max_attachments = settings.FILE_UPLOADS['ATTACHMENTS']['MAX_ATTACHMENTS_ALLOWED']
        to_create_dicts = []
        data = {}
        for i in range(0, max_attachments):
            to_create_dicts.append({
                'file_key': f'file-txt-{i}',
                'name': 'Test txt',
                'description': 'This is a test txt',
                'sequence': i,
            })
            data[f'file-txt-{i}'] = TestFiles.get_simple_uploaded_file('txt')
        data['json'] = json.dumps({'create': to_create_dicts})
        response = self.client.post(path=f'/posts/{Test.post.pk}/attachments/', data=data)
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        num_created = len(response.data['created'])
        self.assertEqual(num_created, max_attachments)
        first_created_dict = response.data['created'][0]

        # Fail - Make an extra attachment
        data = {
            'file-key': TestFiles.get_simple_uploaded_file('jpg'),
            'thumbnail-key': TestFiles.get_simple_uploaded_file('jpg'),
            'json': json.dumps({
                'create': [
                    {
                        'file_key': 'file-key',
                        'thumbnail_key': 'thumbnail-key',
                        'name': 'should fail',
                        'description': None,
                        'sequence': max_attachments,
                    },
                ],
                'update': [],
                'delete': [],
            }),
        }
        response = self.client.post(path=f'/posts/{Test.post.pk}/attachments/', data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Pass - by deleting one as well
        data = {
            'file-key': TestFiles.get_simple_uploaded_file('jpg'),
            'thumbnail-key': TestFiles.get_simple_uploaded_file('jpg'),
            'json': json.dumps({
                'create': [
                    {
                        'file_key': 'file-key',
                        'thumbnail_key': 'thumbnail-key',
                        'name': 'should fail',
                        'description': None,
                        'sequence': max_attachments,
                    },
                ],
                'update': [],
                'delete': [first_created_dict['id']],
            }),
        }
        response = self.client.post(path=f'/posts/{Test.post.pk}/attachments/', data=data)
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
