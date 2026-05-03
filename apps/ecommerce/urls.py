from django.urls import path
from apps.ecommerce import views

urlpatterns = [
    path("orders/", views.orders_page, name="ecommerce_orders"),
    path("products/", views.products_page, name="ecommerce_products"),
    path("customers/", views.customers_page, name="ecommerce_customers"),
    path("dashboard/", views.dashboard_page, name="ecommerce_dashboard"),
]
