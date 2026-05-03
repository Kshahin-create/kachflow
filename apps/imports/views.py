from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from rest_framework import viewsets, decorators, response, status
from apps.accounts.selectors import get_user_projects, user_can_import_data, user_can_upload_excel
from apps.audit.services import log_action
from apps.imports.models import ImportBatch, ImportMapping, ImportTemplate, UploadedFile, WorkbookSheet
from apps.imports.serializers import ImportBatchSerializer, ImportTemplateSerializer, UploadedFileSerializer, WorkbookSheetSerializer
from apps.imports.services import analyze_excel_file, rollback_import_batch, run_import_batch


class UploadedFileViewSet(viewsets.ModelViewSet):
    serializer_class = UploadedFileSerializer

    def get_queryset(self):
        return UploadedFile.objects.filter(project__in=get_user_projects(self.request.user)).select_related("project")

    def perform_create(self, serializer):
        file_obj = self.request.FILES["file"]
        uploaded = serializer.save(
            uploaded_by=self.request.user,
            original_filename=file_obj.name,
            file_type=file_obj.name.split(".")[-1].lower(),
            file_size=file_obj.size,
        )
        analyze_excel_file(uploaded.pk)
        log_action(self.request.user, uploaded.project, "upload_excel", uploaded, request=self.request)

    @decorators.action(detail=True, methods=["get"])
    def sheets(self, request, pk=None):
        uploaded = self.get_object()
        return response.Response(WorkbookSheetSerializer(uploaded.sheets.all(), many=True).data)

    @decorators.action(detail=True, methods=["get"])
    def preview(self, request, pk=None):
        uploaded = self.get_object()
        sheet_name = request.query_params.get("sheet")
        sheet = uploaded.sheets.filter(sheet_name=sheet_name).first() if sheet_name else uploaded.sheets.first()
        return response.Response(WorkbookSheetSerializer(sheet).data if sheet else {})


class ImportTemplateViewSet(viewsets.ModelViewSet):
    serializer_class = ImportTemplateSerializer

    def get_queryset(self):
        return ImportTemplate.objects.filter(project__in=get_user_projects(self.request.user)).prefetch_related("mappings")

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class ImportBatchViewSet(viewsets.ModelViewSet):
    serializer_class = ImportBatchSerializer

    def get_queryset(self):
        return ImportBatch.objects.filter(project__in=get_user_projects(self.request.user))

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @decorators.action(detail=True, methods=["post"])
    def run(self, request, pk=None):
        batch = self.get_object()
        if not user_can_import_data(request.user, batch.project):
            return response.Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        batch = run_import_batch(batch.pk)
        return response.Response(ImportBatchSerializer(batch).data)

    @decorators.action(detail=True, methods=["post"])
    def rollback(self, request, pk=None):
        batch = self.get_object()
        if not user_can_import_data(request.user, batch.project):
            return response.Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        batch = rollback_import_batch(batch.pk)
        return response.Response(ImportBatchSerializer(batch).data)


@login_required
def upload_page(request):
    projects = get_user_projects(request.user)
    if request.method == "POST":
        project = get_object_or_404(projects, pk=request.POST["project"])
        if not user_can_upload_excel(request.user, project):
            raise PermissionDenied
        file_obj = request.FILES["file"]
        uploaded = UploadedFile.objects.create(
            project=project,
            uploaded_by=request.user,
            file=file_obj,
            original_filename=file_obj.name,
            file_type=file_obj.name.split(".")[-1].lower(),
            file_size=file_obj.size,
        )
        analyze_excel_file(uploaded.pk)
        log_action(request.user, project, "upload_excel", uploaded, request=request)
        return redirect("import_sheets", file_id=uploaded.pk)
    return render(request, "imports/upload.html", {"projects": projects})


@login_required
def sheets_page(request, file_id):
    uploaded = get_object_or_404(UploadedFile, pk=file_id, project__in=get_user_projects(request.user))
    return render(request, "imports/sheets.html", {"uploaded": uploaded, "sheets": uploaded.sheets.all()})


@login_required
def preview_page(request, file_id, sheet_name):
    uploaded = get_object_or_404(UploadedFile, pk=file_id, project__in=get_user_projects(request.user))
    sheet = get_object_or_404(uploaded.sheets, sheet_name=sheet_name)
    return render(request, "imports/preview.html", {"uploaded": uploaded, "sheet": sheet})


@login_required
def mapping_page(request, file_id, sheet_name):
    uploaded = get_object_or_404(UploadedFile, pk=file_id, project__in=get_user_projects(request.user))
    sheet = get_object_or_404(WorkbookSheet, uploaded_file=uploaded, sheet_name=sheet_name)
    if not user_can_import_data(request.user, uploaded.project):
        raise PermissionDenied
    if request.method == "POST":
        template = ImportTemplate.objects.create(
            project=uploaded.project,
            name=request.POST.get("name") or f"{uploaded.project.name} {sheet.sheet_name}",
            sheet_name=sheet.sheet_name,
            target_type=request.POST.get("target_type", "generic_dataset"),
            created_by=request.user,
        )
        for column in sheet.detected_columns:
            system_field = request.POST.get(f"map_{column}")
            if system_field:
                ImportMapping.objects.create(template=template, excel_column=column, system_field=system_field)
        batch = ImportBatch.objects.create(project=uploaded.project, uploaded_file=uploaded, template=template, created_by=request.user)
        run_import_batch(batch.pk)
        messages.success(request, "تم تشغيل الاستيراد وحفظ البيانات الخام.")
        return redirect("import_batches")
    return render(request, "imports/mapping.html", {"uploaded": uploaded, "sheet": sheet})


@login_required
def batches_page(request):
    return render(request, "imports/batches.html", {"batches": ImportBatch.objects.filter(project__in=get_user_projects(request.user)).select_related("project", "template").order_by("-created_at")})


@login_required
def templates_page(request):
    return render(request, "imports/templates.html", {"templates": ImportTemplate.objects.filter(project__in=get_user_projects(request.user)).select_related("project")})
