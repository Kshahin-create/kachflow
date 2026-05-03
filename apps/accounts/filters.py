import django_filters
from apps.accounts.models import ProjectMember


class ProjectMemberFilter(django_filters.FilterSet):
    class Meta:
        model = ProjectMember
        fields = ("project", "role", "dashboard_access", "is_active")
