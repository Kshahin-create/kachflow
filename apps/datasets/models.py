from django.conf import settings
from django.db import models


class Dataset(models.Model):
    SOURCE_TYPES = [("excel", "Excel"), ("api", "API"), ("manual", "Manual")]
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="datasets")
    name = models.CharField(max_length=180)
    source_type = models.CharField(max_length=24, choices=SOURCE_TYPES, default="excel")
    source_file = models.ForeignKey("imports.UploadedFile", on_delete=models.SET_NULL, blank=True, null=True)
    sheet_name = models.CharField(max_length=180, blank=True)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class DatasetField(models.Model):
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name="fields")
    name = models.CharField(max_length=180)
    field_type = models.CharField(max_length=40, default="text")
    position = models.PositiveIntegerField(default=0)
    is_required = models.BooleanField(default=False)
    sample_values = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)


class DatasetRow(models.Model):
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name="rows")
    raw_data = models.JSONField(default=dict)
    normalized_data = models.JSONField(default=dict, blank=True, null=True)
    import_batch = models.ForeignKey("imports.ImportBatch", on_delete=models.SET_NULL, blank=True, null=True)
    row_number = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)
