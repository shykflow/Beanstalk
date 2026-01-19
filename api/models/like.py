from django.db import models

class Like(models.Model):
    created_by = models.ForeignKey('User', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    playlist = models.ForeignKey('Playlist', on_delete=models.CASCADE, blank=True, null=True)
    experience = models.ForeignKey('Experience', on_delete=models.CASCADE, blank=True, null=True)
    comment = models.ForeignKey('Comment', on_delete=models.CASCADE, blank=True, null=True)
    post = models.ForeignKey('Post', on_delete=models.CASCADE, blank=True, null=True)

    def save(self, *args, **kwargs) -> None:
        super().save(*args, **kwargs)
        from api.models import (
            Comment,
            Experience,
            Playlist,
            Post,
        )
        comment: Comment = self.comment
        exp: Experience = self.experience
        pl: Playlist = self.playlist
        post: Post = self.post
        if comment is not None:
            comment.calc_total_likes(set_and_save=True)
        if exp is not None:
            exp.calc_total_likes(set_and_save=True)
        if pl is not None:
            pl.calc_total_likes(set_and_save=True)
        if post is not None:
            post.calc_total_likes(set_and_save=True)

    def delete(self, *args, **kwargs):
        from api.models import (
            Comment,
            Experience,
            Playlist,
            Post,
        )
        comment: Comment = self.comment
        exp: Experience = self.experience
        pl: Playlist = self.playlist
        post: Post = self.post
        super_save_value = super().delete(*args, **kwargs)
        if comment is not None:
            comment.calc_total_likes(set_and_save=True)
        if exp is not None:
            exp.calc_total_likes(set_and_save=True)
        if pl is not None:
            pl.calc_total_likes(set_and_save=True)
        if post is not None:
            post.calc_total_likes(set_and_save=True)
        return super_save_value
