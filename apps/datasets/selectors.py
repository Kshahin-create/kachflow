from apps.accounts.selectors import get_user_projects
from apps.datasets.models import Dataset


def list_datasets_for_user(user):
    return Dataset.objects.filter(project__in=get_user_projects(user))
