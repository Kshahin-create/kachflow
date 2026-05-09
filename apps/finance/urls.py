from django.urls import path
from apps.finance import views

urlpatterns = [
    path("accounts/", views.accounts_page, name="finance_accounts"),
    path("accounts/create/", views.accounts_page, name="finance_account_create"),
    path("transactions/", views.transactions_page, name="finance_transactions"),
    path("transactions/create/", views.transaction_create_page, name="finance_transaction_create"),
    path("transactions/<int:pk>/edit/", views.transaction_edit_page, name="finance_transaction_edit"),
    path("categories/", views.categories_page, name="finance_categories"),
    path("cashflow/", views.cashflow_page, name="finance_cashflow"),
]
