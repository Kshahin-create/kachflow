from django.contrib import admin
from apps.datasets.models import Dataset, DatasetField, DatasetRow


class DatasetFieldInline(admin.TabularInline):
    model = DatasetField
    extra = 0


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    list_display = ("name", "project", "source_type", "sheet_name", "created_at")
    search_fields = ("name", "project__name", "sheet_name")
    list_filter = ("source_type",)
    inlines = [DatasetFieldInline]


@admin.register(DatasetRow)
class DatasetRowAdmin(admin.ModelAdmin):
    list_display = ("dataset", "row_number", "created_at")
    search_fields = ("dataset__name",)
    readonly_fields = ("raw_data", "normalized_data")
