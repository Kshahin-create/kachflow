from apps.accounts.selectors import get_user_projects
from apps.reports.models import Report


def list_reports_for_user(user):
    return Report.objects.filter(project__in=get_user_projects(user)) | Report.objects.filter(project__isnull=True, generated_by=user)
