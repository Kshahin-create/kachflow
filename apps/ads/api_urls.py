from django.urls import include, path
from rest_framework.routers import DefaultRouter
from apps.ads.views import AdSpendDailyViewSet, CampaignViewSet, ads_dashboard_api

router = DefaultRouter()
router.register("performance", AdSpendDailyViewSet, basename="api-ad-performance")
router.register("campaigns", CampaignViewSet, basename="api-campaigns")
urlpatterns = [path("", include(router.urls)), path("dashboard/", ads_dashboard_api)]
