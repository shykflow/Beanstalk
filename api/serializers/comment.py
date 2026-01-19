from django.db.models import QuerySet
from rest_framework import serializers

from api.models import Comment, Like
from api.serializers.user import UserViewSerializer


class CommentSerializer(serializers.ModelSerializer):
    created_by = UserViewSerializer(read_only=True)
    user_like = serializers.SerializerMethodField()
    mentions = serializers.SerializerMethodField()

    def get_user_like(self, comment):
        user_likes: QuerySet[Like] = self.context.get('user_likes')
        if user_likes is None:
            return False
        for user_like in user_likes:
            if user_like.comment_id == comment.pk:
                return True
        return False

    def get_mentions(self, comment: Comment):
        # use prefetch_related on querysets to make this faster
        mentioned_users = list(m for m in comment.mentions.all())
        dicts = [
            { 'user_id': m.id, 'username': m.username }
            for m in mentioned_users
        ]
        return dicts

    class Meta:
        model = Comment
        fields = (
            'id',
            'created_by',
            'created_at',
            'text',
            'edited',
            'parent',
            'post',
            'playlist',
            'experience',
            'user_like',
            'mentions',

            # aggregates
            'total_comments',
            'total_likes',
        )
