from apps.accounts.selectors import get_user_projects
from apps.finance.models import Transaction


def list_transactions_for_user(user):
    return Transaction.objects.filter(project__in=get_user_projects(user))
