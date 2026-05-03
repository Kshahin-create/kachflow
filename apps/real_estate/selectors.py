from apps.accounts.selectors import get_user_projects
from apps.real_estate.models import Lease


def list_leases_for_user(user):
    return Lease.objects.filter(project__in=get_user_projects(user))
