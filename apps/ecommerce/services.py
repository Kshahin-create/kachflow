from apps.ecommerce.models import Order


def create_order(**data):
    return Order.objects.create(**data)
