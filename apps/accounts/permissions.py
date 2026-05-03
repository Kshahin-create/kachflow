from rest_framework.permissions import BasePermission
from apps.accounts.selectors import user_can_access_project, user_can_view_financials
from apps.projects.models import Project


class ProjectScopedPermission(BasePermission):
    message = "You do not have access to this project."

    def has_object_permission(self, request, view, obj):
        project = getattr(obj, "project", obj if isinstance(obj, Project) else None)
        return user_can_access_project(request.user, project)


class CanViewFinancials(BasePermission):
    message = "You do not have permission to view financial data."

    def has_object_permission(self, request, view, obj):
        project = getattr(obj, "project", None)
        return user_can_view_financials(request.user, project)
