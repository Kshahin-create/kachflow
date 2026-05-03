from apps.accounts.selectors import get_user_projects
from apps.ecommerce.models import Order


def list_orders_for_user(user):
    return Order.objects.filter(project__in=get_user_projects(user))
