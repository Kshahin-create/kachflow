from django.contrib import admin
from apps.imports.models import ImportBatch, ImportError, ImportMapping, ImportTemplate, RawImportedRow, SheetColumn, UploadedFile, WorkbookSheet


class SheetColumnInline(admin.TabularInline):
    model = SheetColumn
    extra = 0


@admin.register(UploadedFile)
class UploadedFileAdmin(admin.ModelAdmin):
    list_display = ("original_filename", "project", "uploaded_by", "status", "file_size", "uploaded_at")
    search_fields = ("original_filename", "project__name")
    list_filter = ("status", "file_type")
    date_hierarchy = "uploaded_at"


@admin.register(WorkbookSheet)
class WorkbookSheetAdmin(admin.ModelAdmin):
    list_display = ("sheet_name", "uploaded_file", "row_count", "column_count", "created_at")
    search_fields = ("sheet_name", "uploaded_file__original_filename")
    inlines = [SheetColumnInline]


class ImportMappingInline(admin.TabularInline):
    model = ImportMapping
    extra = 0


@admin.register(ImportTemplate)
class ImportTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "project", "sheet_name", "target_type", "created_at")
    search_fields = ("name", "project__name", "sheet_name")
    list_filter = ("target_type",)
    inlines = [ImportMappingInline]


@admin.register(ImportBatch)
class ImportBatchAdmin(admin.ModelAdmin):
    list_display = ("project", "template", "status", "total_rows", "imported_rows", "failed_rows", "created_at")
    search_fields = ("project__name", "template__name")
    list_filter = ("status",)
    date_hierarchy = "created_at"


@admin.register(RawImportedRow)
class RawImportedRowAdmin(admin.ModelAdmin):
    list_display = ("project", "batch", "sheet_name", "row_number", "status", "target_model")
    search_fields = ("project__name", "sheet_name", "target_model")
    list_filter = ("status", "target_model")
    readonly_fields = ("raw_data", "normalized_data")


admin.site.register(ImportError)
