from rest_framework import serializers

from api.models import Experience, NearYouMapping


class NearYouMappingSerializer(serializers.ModelSerializer):
    class Meta:
        model = NearYouMapping
        fields = (
            'image',
            'overlay_opacity',
            'text_color',
            'background_color',
        )

class NearYouMappingFromExperienceSerializer(NearYouMappingSerializer):
    def __init__(self, experience: Experience, *args, **kwargs):
        instance = NearYouMapping(
            image=experience.highlight_image,
            overlay_opacity=kwargs.pop('overlay_opacity', 0.2),
            text_color=kwargs.pop('text_color', '#FFFFFF'),
            background_color=kwargs.pop('background_color', '#000000'),
        )
        super().__init__(instance, *args, **kwargs)
