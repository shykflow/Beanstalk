from rest_framework import serializers

from api.models import Post
from api.serializers.attachment import AttachmentViewSerializer
from django.db.models import Count
from api.serializers.user import UserViewSerializer
from api.serializers.comment import CommentSerializer


class PostValidationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        extra_kwargs = {
            'created_by': {
                'default': serializers.CurrentUserDefault(),
            }
        }
        fields = (
            'id',
            'name',
            'text',
            'created_by',
            'created_at',
            'parent',
            'experience',
            'playlist',
            'visibility',
        )


class PostViewSerializer(serializers.ModelSerializer):
    def __init__(
        self,
        instance,
        num_sample_comments: int=0,
        *args,
        **kwargs):
        self.num_sample_comments = num_sample_comments
        super().__init__(instance, *args, **kwargs)
        if self.context.get('request') is None:
            raise Exception('Request not in context')

    created_by = UserViewSerializer(read_only=True)
    mentions = serializers.SerializerMethodField()
    model = serializers.SerializerMethodField()
    has_comments = serializers.SerializerMethodField()
    sample_comments = serializers.SerializerMethodField()
    user_like = serializers.SerializerMethodField()

    def get_mentions(self, post: Post) -> list[dict]:
        # use prefetch_related on querysets to make this faster
        mentioned_users = list(m for m in post.mentions.all())
        dicts = [
            { 'user_id': m.id, 'username': m.username }
            for m in mentioned_users
        ]
        return dicts

    def get_model(self, post: Post) -> str:
        return 'Post'

    def get_has_comments(self, post: Post) -> bool:
        return post.total_comments > 0

    def get_sample_comments(self, post: Post) -> list[map] :
        if self.num_sample_comments == 0: return []
        comments = post.comments \
            .filter(parent=None) \
            .annotate(like_count=Count('likes')) \
            .order_by('-like_count', '-created_at') \
            [:self.num_sample_comments]
        request_context = {'request':  self.context.get('request')}
        serializer = CommentSerializer(
            comments,
            context=request_context,
            many=True)
        return serializer.data

    def get_user_like(self, post: Post) -> bool:
        request = self.context.get('request')
        return post.likes.filter(pk=request.user.pk).exists()

    class Meta:
        model = Post
        fields = (
            'id',
            'name',
            'text',
            'video',
            'highlight_image',
            'highlight_image_thumbnail',
            'created_by',
            'created_at',
            'parent',
            'experience',
            'playlist',
            'visibility',
            'total_likes',
            'mentions',
            'model',
            'total_comments',
            'has_comments',
            'sample_comments',
            'user_like',
        )


class PostDetailSerializer(PostViewSerializer):

    attachments = AttachmentViewSerializer(many=True, read_only=True)

    class Meta:
        model = Post
        fields = PostViewSerializer.Meta.fields + (
            'attachments',
        )
