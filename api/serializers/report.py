from rest_framework import serializers

from api.models import Report

class ReportSerializer(serializers.ModelSerializer):

    # Auto set the created_by to the request.user
    created_by = serializers.HiddenField(
        default=serializers.CurrentUserDefault())

    def validate(self, data):
        validation = super().validate(data)
        Report.validate(data)
        return validation

    class Meta:
        model = Report
        fields = (
            'created_by',
            'offender',
            'type',
            'details',
            'playlist',
            'experience',
            'post',
            'comment',
        )
