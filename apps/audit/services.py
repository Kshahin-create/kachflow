import gzip
import hashlib
import io
import os

from django.core.management import call_command

from apps.audit.models import AuditLog, DatabaseBackup


def log_action(user=None, project=None, action="", obj=None, description="", metadata=None, request=None):
    ip_address = None
    user_agent = ""
    if request:
        ip_address = request.META.get("HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR", "")).split(",")[0]
        user_agent = request.META.get("HTTP_USER_AGENT", "")
    return AuditLog.objects.create(
        user=user if getattr(user, "is_authenticated", False) else None,
        project=project,
        action=action,
        object_type=obj.__class__.__name__ if obj else "",
        object_id=str(getattr(obj, "pk", "")) if obj else "",
        description=description,
        metadata=metadata or {},
        ip_address=ip_address or None,
        user_agent=user_agent,
    )


def create_database_backup(*, created_by=None, label="نسخة احتياطية"):
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
    backup = DatabaseBackup.objects.create(
        created_by=created_by if getattr(created_by, "is_authenticated", False) else None,
        label=(label or "نسخة احتياطية").strip()[:140],
        sha256=sha,
        size_bytes=len(raw),
        payload_gzip=gz,
    )

    keep_last = int(os.getenv("BACKUP_KEEP_LAST", "20"))
    if keep_last > 0:
        ids = list(DatabaseBackup.objects.order_by("-created_at").values_list("id", flat=True)[keep_last:])
        if ids:
            DatabaseBackup.objects.filter(id__in=ids).delete()
    return backup
