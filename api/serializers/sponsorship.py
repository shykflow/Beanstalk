
from rest_framework import serializers
from sponsorship.models import (
    CategorySponsorship,
)

from api.serializers.user import UserViewSerializer


class SponsorshipViewSerializer(serializers.ModelSerializer):
    """
    This is an abstract class, do not use it as a serializer directly
    """
    user = UserViewSerializer(read_only=True)

    class Meta:
        fields = (
            'id',
            'user',
            'created_at',
            'expires_at',
        )

class CategorySponsorshipViewSerializer(SponsorshipViewSerializer):
    class Meta(SponsorshipViewSerializer.Meta):
        model = CategorySponsorship
        fields = SponsorshipViewSerializer.Meta.fields + (
            'category_id',
            'image',
            'details',
            'experience_ids',
        )
