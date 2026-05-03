from django.urls import include, path
from rest_framework.routers import DefaultRouter
from apps.finance.views import AccountViewSet, CategoryViewSet, TransactionViewSet, finance_summary

router = DefaultRouter()
router.register("accounts", AccountViewSet, basename="api-accounts")
router.register("transactions", TransactionViewSet, basename="api-transactions")
router.register("categories", CategoryViewSet, basename="api-categories")

urlpatterns = [
    path("", include(router.urls)),
    path("summary/", finance_summary, name="api-finance-summary"),
    path("cashflow/", finance_summary, name="api-finance-cashflow"),
]
