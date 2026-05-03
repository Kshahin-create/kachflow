from rest_framework import serializers
from apps.imports.models import UploadedFile, WorkbookSheet, ImportTemplate, ImportMapping, ImportBatch, RawImportedRow


class UploadedFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UploadedFile
        fields = "__all__"
        read_only_fields = ("uploaded_by", "original_filename", "file_type", "file_size", "status", "uploaded_at")


class WorkbookSheetSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkbookSheet
        fields = "__all__"


class ImportMappingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportMapping
        fields = "__all__"


class ImportTemplateSerializer(serializers.ModelSerializer):
    mappings = ImportMappingSerializer(many=True, read_only=True)

    class Meta:
        model = ImportTemplate
        fields = "__all__"
        read_only_fields = ("created_by",)


class ImportBatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportBatch
        fields = "__all__"
        read_only_fields = ("created_by", "status", "total_rows", "imported_rows", "failed_rows", "started_at", "finished_at")


class RawImportedRowSerializer(serializers.ModelSerializer):
    class Meta:
        model = RawImportedRow
        fields = "__all__"
