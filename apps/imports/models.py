from django.conf import settings
from django.db import models


class UploadedFile(models.Model):
    class Status(models.TextChoices):
        UPLOADED = "uploaded", "Uploaded"
        ANALYZING = "analyzing", "Analyzing"
        ANALYZED = "analyzed", "Analyzed"
        FAILED = "failed", "Failed"

    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="uploaded_files")
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True)
    file = models.FileField(upload_to="imports/originals/")
    original_filename = models.CharField(max_length=255)
    file_type = models.CharField(max_length=40, default="xlsx")
    file_size = models.PositiveBigIntegerField(default=0)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.UPLOADED)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    def __str__(self):
        return self.original_filename


class WorkbookSheet(models.Model):
    uploaded_file = models.ForeignKey(UploadedFile, on_delete=models.CASCADE, related_name="sheets")
    sheet_name = models.CharField(max_length=180)
    row_count = models.PositiveIntegerField(default=0)
    column_count = models.PositiveIntegerField(default=0)
    detected_columns = models.JSONField(default=list, blank=True)
    preview_data = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    class Meta:
        unique_together = ("uploaded_file", "sheet_name")

    def __str__(self):
        return self.sheet_name


class SheetColumn(models.Model):
    workbook_sheet = models.ForeignKey(WorkbookSheet, on_delete=models.CASCADE, related_name="columns")
    name = models.CharField(max_length=180)
    detected_type = models.CharField(max_length=40, default="text")
    sample_values = models.JSONField(default=list, blank=True)
    position = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)


class ImportTemplate(models.Model):
    TARGET_TYPES = [
        ("transactions", "Transactions"),
        ("accounts", "Accounts"),
        ("customers", "Customers"),
        ("products", "Products"),
        ("orders", "Orders"),
        ("order_items", "Order Items"),
        ("leases", "Leases"),
        ("installments", "Installments"),
        ("ad_spend", "Ad Spend"),
        ("investments", "Investments"),
        ("generic_dataset", "Generic Dataset"),
    ]

    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="import_templates")
    name = models.CharField(max_length=180)
    sheet_name = models.CharField(max_length=180)
    target_type = models.CharField(max_length=40, choices=TARGET_TYPES, default="generic_dataset")
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class ImportMapping(models.Model):
    template = models.ForeignKey(ImportTemplate, on_delete=models.CASCADE, related_name="mappings")
    excel_column = models.CharField(max_length=180)
    system_field = models.CharField(max_length=180)
    field_type = models.CharField(max_length=40, default="text")
    required = models.BooleanField(default=False)
    default_value = models.CharField(max_length=255, blank=True)
    transformation_rule = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)


class ImportBatch(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        ROLLED_BACK = "rolled_back", "Rolled Back"

    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="import_batches")
    uploaded_file = models.ForeignKey(UploadedFile, on_delete=models.CASCADE, related_name="batches")
    template = models.ForeignKey(ImportTemplate, on_delete=models.PROTECT, related_name="batches")
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.PENDING)
    total_rows = models.PositiveIntegerField(default=0)
    imported_rows = models.PositiveIntegerField(default=0)
    failed_rows = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField(blank=True, null=True)
    finished_at = models.DateTimeField(blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)


class ImportError(models.Model):
    batch = models.ForeignKey(ImportBatch, on_delete=models.CASCADE, related_name="errors")
    row_number = models.PositiveIntegerField()
    column_name = models.CharField(max_length=180, blank=True)
    error_message = models.TextField()
    raw_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)


class RawImportedRow(models.Model):
    class Status(models.TextChoices):
        IMPORTED = "imported", "Imported"
        FAILED = "failed", "Failed"
        ROLLED_BACK = "rolled_back", "Rolled Back"

    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="raw_imported_rows")
    batch = models.ForeignKey(ImportBatch, on_delete=models.CASCADE, related_name="raw_rows")
    sheet_name = models.CharField(max_length=180)
    row_number = models.PositiveIntegerField()
    raw_data = models.JSONField(default=dict)
    normalized_data = models.JSONField(default=dict, blank=True)
    target_model = models.CharField(max_length=120, blank=True)
    target_object_id = models.CharField(max_length=80, blank=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.IMPORTED)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)
