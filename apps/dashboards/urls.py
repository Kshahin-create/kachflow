from django.urls import path
from apps.dashboards.views import dashboard_home

urlpatterns = [
    path("", dashboard_home, name="home"),
    path("dashboard/", dashboard_home, name="dashboard"),
]
