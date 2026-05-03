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
    path("nakhba-api/", views.nakhba_api_settings, name="nakhba_api_settings"),
    path("webhooks/bookings/", views.booking_webhook, name="real_estate_booking_webhook"),
    path("industrial/units/<int:pk>/edit/", views.industrial_unit_edit, name="industrial_unit_edit"),
    path("industrial/leads/<int:pk>/edit/", views.industrial_lead_edit, name="industrial_lead_edit"),
    path("industrial/customers/<int:pk>/edit/", views.industrial_customer_edit, name="industrial_customer_edit"),
]
