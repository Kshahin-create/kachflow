from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db.models import Count, Q
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
    projects = get_user_projects(request.user)
    q = (request.GET.get("q") or "").strip()
    base_qs = Report.objects.filter(project__in=projects).select_related("project")
    if q:
        base_qs = base_qs.filter(Q(title__icontains=q) | Q(project__name__icontains=q) | Q(report_type__icontains=q))

    status_counts = {row["status"]: row["count"] for row in base_qs.values("status").annotate(count=Count("id"))}
    reports_total = base_qs.count()
    generated_count = int(status_counts.get("generated", 0) or 0)
    pending_count = int(status_counts.get("pending", 0) or 0)
    other_count = max(reports_total - generated_count - pending_count, 0)
    reports = base_qs.order_by("-created_at")[:200]
    return render(request, "reports/list.html", {
        "reports": reports,
        "filters": {"q": q},
        "reports_total": reports_total,
        "status_counts": status_counts,
        "summary": {"generated": generated_count, "pending": pending_count, "other": other_count},
    })


from django.shortcuts import render, redirect, get_object_or_404
from .services import generate_project_detailed_report

@login_required
def report_create_page(request):
    if request.method == "POST":
        project_id = request.POST.get("project")
        report_type = request.POST.get("report_type", "monthly_financial")
        start_date = request.POST.get("start_date")
        end_date = request.POST.get("end_date")
        title = request.POST.get("title", f"تقرير تفصيلي - {project_id}")
        
        project = get_object_or_404(Project, pk=project_id, company__owner=request.user)
        
        report = Report.objects.create(
            project=project,
            report_type=report_type,
            title=title,
            period_start=start_date,
            period_end=end_date,
            generated_by=request.user,
            status='pending'
        )
        
        # Generate the report data
        if generate_project_detailed_report(report.id):
            messages.success(request, "تم توليد التقرير بنجاح")
            return redirect("report_detail", pk=report.id)
        else:
            messages.error(request, "حدث خطأ أثناء توليد التقرير")
            
    return render(request, "reports/create.html", {"projects": get_user_projects(request.user)})


from django.contrib import messages
from apps.projects.models import Project

@login_required
def report_detail_page(request, pk):
    report = get_object_or_404(Report, pk=pk)
    # Ensure user has access to this project
    if report.project and not get_user_projects(request.user).filter(pk=report.project.pk).exists():
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
        
    return render(request, "reports/detail.html", {"report": report, "data": report.data})
