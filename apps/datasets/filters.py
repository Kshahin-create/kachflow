import django_filters
from apps.datasets.models import Dataset


class DatasetFilter(django_filters.FilterSet):
    class Meta:
        model = Dataset
        fields = ("project", "source_type", "sheet_name")
