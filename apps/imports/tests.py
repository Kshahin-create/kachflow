from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from openpyxl import Workbook
from apps.accounts.models import ProjectMember
from apps.imports.models import UploadedFile
from apps.imports.services import analyze_excel_file
from apps.projects.models import Company, Project
import tempfile


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class ExcelAnalysisTests(TestCase):
    def test_analyze_workbook_creates_sheets_and_preview(self):
        user = get_user_model().objects.create_user("owner", password="pw")
        company = Company.objects.create(name="Demo", owner=user)
        project = Project.objects.create(company=company, name="Import Project")
        ProjectMember.objects.create(user=user, project=project, can_upload_excel=True, can_import_data=True)
        wb = Workbook()
        ws = wb.active
        ws.title = "Sales"
        ws.append(["date", "amount"])
        ws.append(["2026-01-01", 120])
        tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
        wb.save(tmp.name)
        with open(tmp.name, "rb") as fh:
            uploaded = UploadedFile.objects.create(project=project, uploaded_by=user, file=ContentFile(fh.read(), name="demo.xlsx"), original_filename="demo.xlsx")
        analyze_excel_file(uploaded.pk)
        sheet = uploaded.sheets.get(sheet_name="Sales")
        self.assertEqual(sheet.detected_columns, ["date", "amount"])
        self.assertEqual(sheet.preview_data[0]["amount"], 120)
