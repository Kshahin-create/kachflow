from django.urls import include, path
from rest_framework.routers import DefaultRouter
from apps.ecommerce.views import CustomerViewSet, OrderViewSet, ProductViewSet, ecommerce_dashboard_api

router = DefaultRouter()
router.register("orders", OrderViewSet, basename="api-orders")
router.register("products", ProductViewSet, basename="api-products")
router.register("customers", CustomerViewSet, basename="api-customers")
urlpatterns = [path("", include(router.urls)), path("dashboard/", ecommerce_dashboard_api)]
