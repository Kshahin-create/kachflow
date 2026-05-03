from django.contrib import admin
from apps.finance.models import Account, Category, CurrencyRate, Transaction, Transfer


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("name", "project", "company", "account_type", "currency", "current_balance", "is_sensitive")
    search_fields = ("name", "project__name", "company__name")
    list_filter = ("account_type", "currency", "is_sensitive")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "type", "project", "parent", "created_at")
    search_fields = ("name", "project__name")
    list_filter = ("type",)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("date", "project", "account", "transaction_type", "amount", "currency", "source")
    search_fields = ("description", "project__name", "account__name")
    list_filter = ("transaction_type", "source", "currency")
    date_hierarchy = "date"


admin.site.register(Transfer)
admin.site.register(CurrencyRate)
