from api.models import (
    Playlist,
)
from api.testing_overrides import GlobalTestCredentials
from . import SilenceableAPITestCase

class Test(SilenceableAPITestCase):

    playlistA: Playlist
    playlistB: Playlist

    def setUpTestData():
        Test.playlistA = Playlist.objects.create(
            name="a",
            description="aa",
            created_by=GlobalTestCredentials.user,
        )
        Test.playlistB = Playlist.objects.create(
            name="b",
            description="bb",
            created_by=GlobalTestCredentials.user,
        )

    def setUp(self):
        super().setUp()
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {GlobalTestCredentials.token}',
        )


    def test_get_playlists_saved_but_not_pinned_by_user(self):
        GlobalTestCredentials.user.pinned_playlists.add(
            Test.playlistA,
            through_defaults={'position':1})
        GlobalTestCredentials.user.saved_playlists.add(Test.playlistA)
        GlobalTestCredentials.user.saved_playlists.add(Test.playlistB)
        user_id = GlobalTestCredentials.user.id
        response = self.client.get(f'/playlists/?page=1&not_pinned_by={user_id}&saved_by={user_id}')
        assert response.data['count'] == 1
        assert response.data['results'][0]['id'] == Test.playlistB.id

    def test_get_playlists_created_but_not_pinned_by_user(self):
        GlobalTestCredentials.user.pinned_playlists.add(
            Test.playlistA,
            through_defaults={'position':1})
        user_id = GlobalTestCredentials.user.id
        response = self.client.get(f'/playlists/?page=1&not_pinned_by={user_id}&created_by={user_id}')
        assert response.data['count'] == 1
        assert response.data['results'][0]['id'] == Test.playlistB.id
