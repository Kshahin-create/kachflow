from apps.accounts.models import ProjectMember
from apps.projects.models import Project


def _is_global_admin(user):
    return bool(user and user.is_authenticated and (user.is_superuser or user.is_staff))


def get_user_projects(user):
    if not user or not user.is_authenticated:
        return Project.objects.none()
    if _is_global_admin(user):
        return Project.objects.select_related("company").all()
    return Project.objects.select_related("company").filter(members__user=user, members__is_active=True).distinct()


def get_project_membership(user, project):
    if not user or not user.is_authenticated or not project:
        return None
    return ProjectMember.objects.filter(user=user, project=project, is_active=True).first()


def user_can_access_project(user, project):
    return _is_global_admin(user) or get_project_membership(user, project) is not None


def _flag(user, project, field):
    if _is_global_admin(user):
        return True
    membership = get_project_membership(user, project)
    return bool(membership and getattr(membership, field, False))


def user_can_view_dashboard(user, project):
    return _flag(user, project, "can_view_dashboard")


def user_can_view_financials(user, project):
    return _flag(user, project, "can_view_financials")


def user_can_upload_excel(user, project):
    return _flag(user, project, "can_upload_excel")


def user_can_import_data(user, project):
    return _flag(user, project, "can_import_data")


def user_can_manage_project_users(user, project):
    return _flag(user, project, "can_manage_users")


def user_can_view_sensitive_accounts(user, project):
    return _flag(user, project, "can_view_sensitive_accounts")


def user_can_view_partner_dashboard(user, project):
    return _flag(user, project, "can_view_partner_dashboard")
