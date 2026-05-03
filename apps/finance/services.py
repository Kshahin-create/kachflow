from apps.finance.models import Transaction


def create_transaction(**data):
    return Transaction.objects.create(**data)
