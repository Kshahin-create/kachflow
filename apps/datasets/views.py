from rest_framework import viewsets
from apps.datasets.models import Dataset, DatasetRow
from apps.datasets.serializers import DatasetRowSerializer, DatasetSerializer
from apps.accounts.selectors import get_user_projects


class DatasetViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DatasetSerializer
    def get_queryset(self):
        return Dataset.objects.filter(project__in=get_user_projects(self.request.user))


class DatasetRowViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DatasetRowSerializer
    def get_queryset(self):
        return DatasetRow.objects.filter(dataset__project__in=get_user_projects(self.request.user))
