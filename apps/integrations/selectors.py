from apps.accounts.selectors import get_user_projects
from apps.integrations.models import ApiConnection


def list_api_connections_for_user(user):
    return ApiConnection.objects.filter(project__in=get_user_projects(user))
