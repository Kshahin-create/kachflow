import django_filters
from apps.audit.models import AuditLog


class AuditLogFilter(django_filters.FilterSet):
    class Meta:
        model = AuditLog
        fields = ("project", "action", "object_type")
