from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from rest_framework import viewsets, decorators, response
from apps.accounts.selectors import get_user_projects
from apps.dashboards.services import get_investment_metrics
from apps.investments.models import Asset
from apps.investments.serializers import AssetSerializer


class AssetViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AssetSerializer
    def get_queryset(self):
        return Asset.objects.filter(project__in=get_user_projects(self.request.user)) | Asset.objects.filter(owner=self.request.user, project__isnull=True)


@decorators.api_view(["GET"])
def investments_dashboard_api(request):
    return response.Response(get_investment_metrics(request.user, request.query_params.get("project")))


@login_required
def assets_page(request):
    return render(request, "investments/assets.html", {"assets": Asset.objects.filter(project__in=get_user_projects(request.user))[:100]})


@login_required
def dashboard_page(request):
    return render(request, "investments/dashboard.html", {})
