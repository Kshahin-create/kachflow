from django.urls import path
from apps.ecommerce import views

urlpatterns = [
    path("", views.dashboard, name="ecommerce_dashboard"),
    path("orders/", views.orders_page, name="ecommerce_orders"),
    path("orders/<int:order_id>/", views.order_detail, name="ecommerce_order_detail"),
    path("products/", views.products_page, name="ecommerce_products"),
    path("products/<int:product_id>/", views.product_detail, name="ecommerce_product_detail"),
    path("customers/", views.customers_page, name="ecommerce_customers"),
    path("customers/<int:customer_id>/", views.customer_detail, name="ecommerce_customer_detail"),
    path("promo-codes/", views.promo_codes_page, name="ecommerce_promo_codes"),
    path("collections/", views.collections_page, name="ecommerce_collections"),
    path("wuilt-api/", views.wuilt_api_settings, name="ecommerce_wuilt_api_settings"),
    path("webhooks/wuilt/", views.wuilt_webhook, name="ecommerce_wuilt_webhook"),
    path("dashboard/", views.dashboard, name="ecommerce_dashboard_alias"),
]
