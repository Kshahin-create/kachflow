import django_filters
from apps.finance.models import Account, Transaction


class AccountFilter(django_filters.FilterSet):
    class Meta:
        model = Account
        fields = ("project", "account_type", "currency", "is_sensitive")


class TransactionFilter(django_filters.FilterSet):
    date_from = django_filters.DateFilter(field_name="date", lookup_expr="gte")
    date_to = django_filters.DateFilter(field_name="date", lookup_expr="lte")

    class Meta:
        model = Transaction
        fields = ("project", "account", "transaction_type", "category", "date_from", "date_to")
