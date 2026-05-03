from apps.accounts.selectors import get_user_projects
from apps.audit.models import AuditLog


def list_audit_logs_for_user(user):
    if user.is_staff:
        return AuditLog.objects.all()
    return AuditLog.objects.filter(project__in=get_user_projects(user))
