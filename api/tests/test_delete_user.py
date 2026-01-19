from django.db.models import Q
from rest_framework import status
from rest_framework.authtoken.models import Token

from api.models import (
    Comment,
    Experience,
    ExperienceAccept,
    Like,
    Playlist,
    PlaylistAccept,
    Post,
    User,
)
from . import SilenceableAPITestCase

class Test(SilenceableAPITestCase):

    def test_hard_delete(self):
        # user_A and all associated content should be deleted.
        user_A: User = User.objects.create(
            username='test_A',
            email='test_A@email.com',
            email_verified=True,
            name="Test_User_A")
        token_A = Token.objects.create(
            user=user_A)
        # user_B and all content not associated with user_A shouldn't get deleted.
        user_B: User = User.objects.create(
            username='test_B',
            email='test_B@email.com',
            email_verified=True,
             name="Test_User_B")

        experience_A: Experience = Experience.objects.create(
            name = 'test_experience_A',
            created_by = user_A)
        experience_A_accept_A = ExperienceAccept.objects.create(
            user=user_A,
            experience=experience_A)
        experience_B: Experience = Experience.objects.create(
            name = 'test_experience_B',
            created_by = user_B)
        experience_A_accept_B = ExperienceAccept.objects.create(
            user=user_A,
            experience=experience_B)
        experience_B_accept_B = ExperienceAccept.objects.create(
            user=user_B,
            experience=experience_B)

        playlist_A: Playlist = Playlist.objects.create(
            name = 'test_playlist_A',
            created_by = user_A)
        playlist_A_accept_A = PlaylistAccept.objects.create(
            user=user_A,
            playlist=playlist_A)
        playlist_B: Playlist = Playlist.objects.create(
            name = 'test_playlist_B',
            created_by = user_B)
        playlist_A_accept_B = PlaylistAccept.objects.create(
            user=user_A,
            playlist=playlist_B)
        playlist_B_accept_B = PlaylistAccept.objects.create(
            user=user_B,
            playlist=playlist_B)

        post_A: Post = Post.objects.create(
            created_by=user_A,
            name='test_post_A')
        post_B: Post = Post.objects.create(
            created_by=user_B,
            name='test_post_B')

        comment_A_on_post_A: Comment = Comment.objects.create(
            created_by=user_A,
            post=post_A)
        comment_B_on_post_A: Comment = Comment.objects.create(
            created_by=user_B,
            post=post_A)
        comment_A_on_post_B: Comment = Comment.objects.create(
            created_by=user_A,
            post=post_B)
        comment_B_on_post_B: Comment = Comment.objects.create(
            created_by=user_B,
            post=post_B)

        experience_A.likes.add(user_A)
        experience_A.likes.add(user_B)
        experience_B.likes.add(user_A)
        experience_B.likes.add(user_B)
        playlist_A.likes.add(user_A)
        playlist_A.likes.add(user_B)
        playlist_B.likes.add(user_A)
        playlist_B.likes.add(user_B)
        post_A.likes.add(user_A)
        post_A.likes.add(user_B)
        post_B.likes.add(user_A)
        post_B.likes.add(user_B)
        comment_A_on_post_A.likes.add(user_A)
        comment_A_on_post_A.likes.add(user_B)
        comment_B_on_post_A.likes.add(user_A)
        comment_B_on_post_A.likes.add(user_B)
        comment_A_on_post_B.likes.add(user_A)
        comment_A_on_post_B.likes.add(user_B)
        comment_B_on_post_B.likes.add(user_A)
        comment_B_on_post_B.likes.add(user_B)
        
        # Counting all the content before deleting the user_to_delete
        # Do not create content for this test after or during this block.
        total_experiences = Experience.objects.count()
        total_experience_accepts = ExperienceAccept.objects.count()
        total_playlists = Playlist.objects.count()
        total_playlist_accepts = PlaylistAccept.objects.count()
        total_posts = Post.objects.count()
        total_likes = Like.objects.count()
        total_comments = Comment.objects.count()
        experience_count_A = Experience.objects.filter(created_by=user_A).count()
        experience_accept_count_A = ExperienceAccept.objects.filter(user=user_A).count()
        playlist_count_A = Playlist.objects.filter(created_by=user_A).count()
        playlist_accept_count_A = PlaylistAccept.objects.filter(user=user_A).count()
        post_count_A = Post.objects.filter(created_by=user_A).count()
        like_count_A = Like.objects.filter(created_by=user_A).count()
        
        # user_B's likes of user_A's content. These likes also get deleted.
        like_count_B_of_A = Like.objects.filter(
            Q(created_by=user_B) & 
            (Q(experience__created_by=user_A) |
                Q(playlist__created_by=user_A) |
                Q(post__created_by=user_A) |
                Q(comment__created_by=user_A) |
                # likes on user_B's comments on user_A's content.
                (Q(comment__created_by=user_B) &
                    (Q(comment__experience__created_by=user_A) |
                    Q(comment__playlist__created_by=user_A) |
                    Q(comment__post__created_by=user_A) |
                    Q(comment__parent__created_by=user_A))))) \
                .count()
        
        comment_count_A = Comment.objects.filter(created_by=user_A).count()
        # user_B's comments on user_A's content. These comments also get deleted. 
        comment_count_B_of_A = Comment.objects.filter(
            Q(created_by=user_B) &
            (Q(experience__created_by=user_A) |
                Q(playlist__created_by=user_A) |
                Q(post__created_by=user_A) |
                Q(parent__created_by=user_A))) \
            .count()
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token_A}')
        # user_A deleted here
        response = self.client.delete(f'/users/delete/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # No users match deleted user's id
        self.assertFalse(User.objects.filter(id=user_A.id).exists())

        # user_A experiences are gone
        self.assertFalse(Experience.objects.filter(created_by=user_A).exists())

        # All other experiences are still there
        self.assertEqual(Experience.objects.count(), total_experiences - experience_count_A)

        # user_A ExperienceAccepts are gone
        self.assertFalse(ExperienceAccept.objects.filter(user=user_A).exists())

        # All other ExperienceAccepts are still there
        self.assertEqual(ExperienceAccept.objects.count(), total_experience_accepts - experience_accept_count_A)

        # user_A playlists are gone.
        self.assertFalse(Playlist.objects.filter(created_by=user_A).exists())

        # All other playlists are still there
        self.assertEqual(Playlist.objects.count(), total_playlists - playlist_count_A)

        # user_A PlaylistAccepts are gone
        self.assertFalse(PlaylistAccept.objects.filter(user=user_A).exists())

        # All other PlaylistAccepts are still there
        self.assertEqual(PlaylistAccept.objects.count(), total_playlist_accepts - playlist_accept_count_A)

        # user_A Posts are gone
        self.assertFalse(Post.objects.filter(created_by=user_A).exists())

        # All other Posts are still there
        self.assertEqual(Post.objects.count(), total_posts - post_count_A)

        # user_A Likes are gone
        self.assertFalse(Like.objects.filter(created_by=user_A).exists())

        # All Likes made by other users on non user_A content are still there
        self.assertEqual(Like.objects.count(), total_likes - like_count_A - like_count_B_of_A)

        # user_A Comments are gone
        self.assertFalse(Comment.objects.filter(created_by=user_A).exists())

        # All Comments made by other users on non user_A content are still there
        self.assertEqual(Comment.objects.count(), total_comments - comment_count_A - comment_count_B_of_A)
