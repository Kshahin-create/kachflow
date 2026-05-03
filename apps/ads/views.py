from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from rest_framework import viewsets, decorators, response
from apps.accounts.selectors import get_user_projects
from apps.ads.models import AdPerformanceMetric, AdSpendDaily, Campaign
from apps.ads.serializers import AdPerformanceMetricSerializer, AdSpendDailySerializer, CampaignSerializer
from apps.dashboards.services import get_ads_metrics


class CampaignViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CampaignSerializer
    def get_queryset(self):
        return Campaign.objects.filter(ad_account__project__in=get_user_projects(self.request.user))


class AdSpendDailyViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AdSpendDailySerializer
    def get_queryset(self):
        return AdSpendDaily.objects.filter(project__in=get_user_projects(self.request.user))


@decorators.api_view(["GET"])
def ads_dashboard_api(request):
    project_id = request.query_params.get("project")
    return response.Response(get_ads_metrics(request.user, project_id) if project_id else {})


@login_required
def performance_page(request):
    return render(request, "ads/performance.html", {"metrics": AdPerformanceMetric.objects.filter(project__in=get_user_projects(request.user))[:100]})


@login_required
def campaigns_page(request):
    return render(request, "ads/campaigns.html", {"campaigns": Campaign.objects.filter(ad_account__project__in=get_user_projects(request.user))[:100]})


@login_required
def dashboard_page(request):
    return render(request, "ads/dashboard.html", {})
