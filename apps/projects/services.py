from apps.accounts.models import ProjectMember
from apps.projects.models import Project


def create_project_with_owner(*, company, owner, name, project_type="generic", base_currency="SAR", **extra):
    project = Project.objects.create(company=company, name=name, project_type=project_type, base_currency=base_currency, **extra)
    ProjectMember.objects.create(
        project=project,
        user=owner,
        role=ProjectMember.Role.OWNER,
        dashboard_access=ProjectMember.DashboardAccess.FULL,
        can_view_dashboard=True,
        can_view_financials=True,
        can_manage_users=True,
        can_upload_excel=True,
        can_import_data=True,
        can_view_partner_dashboard=True,
    )
    return project
