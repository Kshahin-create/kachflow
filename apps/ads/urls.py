from django.urls import path
from apps.ads import views

urlpatterns = [
    path("performance/", views.performance_page, name="ads_performance"),
    path("campaigns/", views.campaigns_page, name="ads_campaigns"),
    path("dashboard/", views.dashboard_page, name="ads_dashboard"),
]
