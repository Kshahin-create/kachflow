from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from rest_framework import viewsets, decorators, response
from apps.accounts.selectors import get_user_projects
from apps.reports.models import Report
from apps.reports.serializers import ReportSerializer


class ReportViewSet(viewsets.ModelViewSet):
    serializer_class = ReportSerializer

    def get_queryset(self):
        return Report.objects.filter(project__in=get_user_projects(self.request.user)) | Report.objects.filter(project__isnull=True, generated_by=self.request.user)

    def perform_create(self, serializer):
        serializer.save(generated_by=self.request.user, data={})


@decorators.api_view(["POST"])
def generate_report_api(request):
    serializer = ReportSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    report = serializer.save(generated_by=request.user, data={})
    return response.Response(ReportSerializer(report).data)


@login_required
def reports_page(request):
    return render(request, "reports/list.html", {"reports": Report.objects.filter(project__in=get_user_projects(request.user))[:100]})


@login_required
def report_create_page(request):
    return render(request, "reports/create.html", {"projects": get_user_projects(request.user)})


@login_required
def report_detail_page(request, pk):
    return render(request, "reports/detail.html", {"report": Report.objects.get(pk=pk)})
