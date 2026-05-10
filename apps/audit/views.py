from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import FileResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.core.management import call_command
from django.utils.http import url_has_allowed_host_and_scheme
from rest_framework import viewsets
import gzip
import hashlib
import io
import json
import os
import tempfile

from apps.accounts.selectors import get_user_projects
from apps.audit.models import AuditLog, DatabaseBackup
from apps.audit.serializers import AuditLogSerializer


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditLogSerializer

    def get_queryset(self):
        if self.request.user.is_staff:
            return AuditLog.objects.all()
        return AuditLog.objects.filter(project__in=get_user_projects(self.request.user))


@login_required
def audit_log_page(request):
    logs = AuditLog.objects.all() if request.user.is_staff else AuditLog.objects.filter(project__in=get_user_projects(request.user))
    return render(request, "users/audit_log.html", {"logs": logs[:200], "active": "audit_log"})


@login_required
def settings_page(request):
    backups = []
    if request.user.is_staff:
        backups = list(DatabaseBackup.objects.all()[:30])

    if request.method == "POST":
        if not request.user.is_staff:
            return HttpResponseForbidden()

        action = request.POST.get("action")
        if action == "create_backup":
            label = (request.POST.get("label") or "").strip()
            if not label:
                label = "نسخة احتياطية"
            out = io.StringIO()
            call_command(
                "dumpdata",
                stdout=out,
                use_natural_foreign_keys=True,
                use_natural_primary_keys=True,
                exclude=["contenttypes", "auth.permission"],
                indent=2,
            )
            raw = out.getvalue().encode("utf-8")
            gz = gzip.compress(raw, compresslevel=9)
            sha = hashlib.sha256(raw).hexdigest()
            DatabaseBackup.objects.create(
                created_by=request.user,
                label=label,
                sha256=sha,
                size_bytes=len(raw),
                payload_gzip=gz,
            )
            messages.success(request, "تم إنشاء نسخة احتياطية بنجاح.")
            next_url = (request.POST.get("next") or "").strip()
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
                return redirect(next_url)
            return redirect("settings")

        messages.error(request, "طلب غير معروف.")
        return redirect("settings")

    return render(request, "users/settings.html", {"backups": backups, "tab": "overview", "active": "settings"})


@login_required
def roles_page(request):
    return render(request, "users/roles.html", {})


@login_required
def backup_download(request, backup_id: int):
    if not request.user.is_staff:
        return HttpResponseForbidden()

    backup = get_object_or_404(DatabaseBackup, pk=backup_id)
    data = gzip.decompress(backup.payload_gzip)
    safe_label = (backup.label or "backup").replace('"', "").replace("\\", "").strip()[:80] or "backup"
    filename = f"{safe_label}-{backup.created_at.date().isoformat()}.json"
    resp = FileResponse(io.BytesIO(data), as_attachment=True, filename=filename, content_type="application/octet-stream")
    resp["X-Content-Type-Options"] = "nosniff"
    return resp


@login_required
def backups_page(request):
    if not request.user.is_staff:
        return HttpResponseForbidden()

    backups = list(DatabaseBackup.objects.all()[:50])
    return render(request, "users/settings.html", {"backups": backups, "tab": "backups", "active": "backups_page"})


@login_required
def restore_page(request):
    if not request.user.is_staff:
        return HttpResponseForbidden()

    if request.method == "POST":
        action = request.POST.get("action")
        if action != "restore_backup":
            messages.error(request, "طلب غير معروف.")
            return redirect("restore_page")

        uploaded = request.FILES.get("backup_file")
        if not uploaded:
            messages.error(request, "اختار ملف JSON الأول.")
            return redirect("restore_page")

        raw_bytes = uploaded.read()
        decoded = None
        for enc in ("utf-8", "utf-8-sig"):
            try:
                decoded = raw_bytes.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        if decoded is None:
            messages.error(request, "الملف لازم يكون UTF-8.")
            return redirect("restore_page")

        try:
            json.loads(decoded)
        except json.JSONDecodeError:
            messages.error(request, "الملف مش JSON صالح.")
            return redirect("restore_page")

        tmp_path = ""
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp:
                tmp.write(raw_bytes)
                tmp_path = tmp.name
            call_command("loaddata", tmp_path)
            messages.success(request, "تم استرجاع البيانات بنجاح.")
        except Exception as exc:
            messages.error(request, f"فشل استرجاع البيانات: {exc}")
        finally:
            if tmp_path:
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

        return redirect("restore_page")

    return render(request, "users/settings.html", {"tab": "restore", "active": "restore_page"})
