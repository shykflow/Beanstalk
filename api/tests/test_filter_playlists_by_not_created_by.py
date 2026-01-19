from api.models import (
    Playlist,
    User,
)
from api.testing_overrides import GlobalTestCredentials
from . import SilenceableAPITestCase

class Test(SilenceableAPITestCase):

    playlistA: Playlist
    playlistB: Playlist
    userB: User

    def setUpTestData():
        Test.userB = User.objects.create(
            username= 'userB',
            email = 'userB@email.com',
            email_verified = True,
        )
        Test.playlistA = Playlist.objects.create(
            name="a",
            description="aa",
            created_by=GlobalTestCredentials.user,
        )
        Test.playlistB = Playlist.objects.create(
            name="b",
            description="bb",
            created_by=Test.userB,
        )

    def setUp(self):
        super().setUp()
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {GlobalTestCredentials.token}')


    def test_get_playlists_saved_but_not_created_by_user(self):
        GlobalTestCredentials.user.saved_playlists.add(Test.playlistA)
        GlobalTestCredentials.user.saved_playlists.add(Test.playlistB)
        user_id = GlobalTestCredentials.user.id
        response = self.client.get(f'/playlists/?page=1&not_created_by={user_id}&saved_by={user_id}')
        assert response.data['count'] == 1
        assert response.data['results'][0]['id'] == Test.playlistB.id
