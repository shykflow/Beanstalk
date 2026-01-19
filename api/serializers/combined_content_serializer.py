from rest_framework import serializers
from api.models import Experience, Playlist, Post
from api.serializers.experience import ExperienceViewSerializer
from api.serializers.playlist import PlaylistViewSerializer
from api.serializers.post import PostViewSerializer


class CombinedContentSerializer(serializers.Serializer):
    """Handles Playlist, Experience, or Post with its own serializer"""

    def get_serializer(self, model):
        if model is Experience:
            return ExperienceViewSerializer
        if model is Playlist:
            return PlaylistViewSerializer
        if model is Post:
            return PostViewSerializer
        raise TypeError()

    def to_representation(self, instance):
        serializer = self.get_serializer(instance.__class__)
        return serializer(instance, context=self.context).data
