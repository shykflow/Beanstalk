from rest_framework import serializers


class CostRatingSerializer(serializers.Serializer):
    rating = serializers.IntegerField(max_value=4, min_value=0)
