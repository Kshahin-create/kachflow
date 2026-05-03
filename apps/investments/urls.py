from django.urls import path
from apps.investments import views

urlpatterns = [
    path("assets/", views.assets_page, name="investments_assets"),
    path("dashboard/", views.dashboard_page, name="investments_dashboard"),
]
