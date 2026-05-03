from apps.accounts.selectors import get_user_projects
from apps.ads.models import AdSpendDaily


def list_ad_spend_for_user(user):
    return AdSpendDaily.objects.filter(project__in=get_user_projects(user))
