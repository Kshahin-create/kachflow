from django.contrib.auth.decorators import login_required
from django.urls import path
from apps.real_estate import views

urlpatterns = [
    path("properties/", login_required(views.properties_page), name="real_estate_properties"),
    path("units/", login_required(views.units_page), name="real_estate_units"),
    path("tenants/", login_required(views.tenants_page), name="real_estate_tenants"),
    path("leases/", login_required(views.leases_page), name="real_estate_leases"),
    path("collections/", login_required(views.collections_page), name="real_estate_collections"),
    path("installments/", login_required(views.installments_page), name="real_estate_installments"),
    path("dashboard/", login_required(views.dashboard_page), name="real_estate_dashboard"),
    path("analytics/", login_required(views.analytics_page), name="real_estate_analytics"),
    path("bookings/", login_required(views.bookings_page), name="real_estate_bookings"),
    path("customers/", login_required(views.customers_page), name="real_estate_customers"),
    path("customers/<str:user_id>/", login_required(views.customer_detail_page), name="real_estate_customer_detail"),
    path("tenant-accounts/", login_required(views.tenant_accounts_page), name="real_estate_tenant_accounts"),
    path("tenant-accounts/<str:tenant_account_id>/", login_required(views.tenant_account_detail_page), name="real_estate_tenant_account_detail"),
    path("invoices/", login_required(views.invoices_page), name="real_estate_invoices"),
    path("audit-log/", login_required(views.audit_log_page), name="real_estate_audit_log"),
    path("users/", login_required(views.users_page), name="real_estate_users"),
    path("nakhba-api/", login_required(views.nakhba_api_settings), name="nakhba_api_settings"),
    path("nakhba-api/docs/", login_required(views.nakhba_api_docs), name="real_estate_nakhba_api_docs"),
    path("webhooks/bookings/", views.booking_webhook, name="real_estate_booking_webhook"),
    path("industrial/units/<int:pk>/edit/", views.industrial_unit_edit, name="industrial_unit_edit"),
    path("industrial/leads/<int:pk>/edit/", views.industrial_lead_edit, name="industrial_lead_edit"),
    path("industrial/customers/<int:pk>/edit/", views.industrial_customer_edit, name="industrial_customer_edit"),
]
