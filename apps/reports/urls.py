from django.urls import path
from apps.reports import views

urlpatterns = [
    path("", views.reports_page, name="reports"),
    path("create/", views.report_create_page, name="report_create"),
    path("<int:pk>/", views.report_detail_page, name="report_detail"),
]
