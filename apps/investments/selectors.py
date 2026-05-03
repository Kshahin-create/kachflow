from apps.accounts.selectors import get_user_projects
from apps.investments.models import Asset


def list_assets_for_user(user):
    return Asset.objects.filter(project__in=get_user_projects(user)) | Asset.objects.filter(owner=user, project__isnull=True)
