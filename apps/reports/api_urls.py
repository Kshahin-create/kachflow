from django.urls import include, path
from rest_framework.routers import DefaultRouter
from apps.reports.views import ReportViewSet, generate_report_api

router = DefaultRouter()
router.register("", ReportViewSet, basename="api-reports")
urlpatterns = [path("generate/", generate_report_api), path("", include(router.urls))]
