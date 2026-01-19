from rest_framework import viewsets, mixins

from api.models import Report
from api.serializers.report import ReportSerializer

class ReportViewSet(viewsets.GenericViewSet, mixins.CreateModelMixin):
    queryset = Report.objects.all()
    serializer_class = ReportSerializer
