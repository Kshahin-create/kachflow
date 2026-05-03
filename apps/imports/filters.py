import django_filters
from apps.imports.models import ImportBatch, UploadedFile


class UploadedFileFilter(django_filters.FilterSet):
    class Meta:
        model = UploadedFile
        fields = ("project", "status", "file_type")


class ImportBatchFilter(django_filters.FilterSet):
    class Meta:
        model = ImportBatch
        fields = ("project", "status", "template")
