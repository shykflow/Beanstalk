from rest_framework import serializers

from api.models import Attachment

class AttachmentSerializerBaseMeta:
    model = Attachment
    fields = (
        'id',
        'name',
        'description',
        'sequence',
    )

class AttachmentCreateSerializer(serializers.ModelSerializer):
    file_key = serializers.CharField()
    class Meta(AttachmentSerializerBaseMeta):
        fields = fields = AttachmentSerializerBaseMeta.fields + (
            'file_key',
        )

class AttachmentUpdateSerializer(serializers.ModelSerializer):
    class Meta(AttachmentSerializerBaseMeta):
        pass

class AttachmentViewSerializer(serializers.ModelSerializer):
    class Meta(AttachmentSerializerBaseMeta):
        fields = AttachmentSerializerBaseMeta.fields + (
            'file',
            'type',
            'thumbnail',
        )
