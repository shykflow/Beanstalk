from rest_framework import status

from api.models import (
    Playlist,
    Post,
)
from api.testing_overrides import GlobalTestCredentials
from . import SilenceableAPITestCase

class Test(SilenceableAPITestCase):
    playlist: Playlist
    post: Post

    def setUp(self):
        super().setUp()
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {GlobalTestCredentials.token}')
        Test.playlist = Playlist.objects.create(
            name="Post about this",
            description="Going to create and delete a post about this",
            created_by=GlobalTestCredentials.user)
        Test.post = Post.objects.create(
            name="Delete this",
            text="This is going to be soft deleted",
            playlist=Test.playlist,
            created_by=GlobalTestCredentials.user)

    def test_soft_delete_orm(self):
        Test.post.delete()
        deleted_post = Post.objects.filter(pk=Test.post.pk).first()
        self.assertIsNone(deleted_post)
        deleted_post = Post.all_objects.filter(pk=Test.post.pk).first()
        self.assertIsNotNone(deleted_post)

    def test_soft_delete_api_with_orm_delete(self):
        response = self.client.get(f'/posts/{Test.post.pk}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        Test.post.delete()
        response = self.client.get(f'/posts/{Test.post.pk}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_soft_delete_api_with_api_delete(self):
        response = self.client.get(f'/posts/{Test.post.pk}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.client.delete(f'/posts/{Test.post.pk}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        response = self.client.get(f'/posts/{Test.post.pk}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
