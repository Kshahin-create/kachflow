from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from rest_framework import viewsets
from apps.accounts.selectors import get_user_projects
from apps.audit.models import AuditLog
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
    return render(request, "users/audit_log.html", {"logs": logs[:200]})


@login_required
def settings_page(request):
    return render(request, "users/settings.html", {})


@login_required
def roles_page(request):
    return render(request, "users/roles.html", {})
