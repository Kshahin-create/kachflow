import json
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.cache import cache
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from rest_framework import viewsets, decorators, response, status
from apps.accounts.models import ProjectMember, ProjectInvitation
from apps.accounts.selectors import get_user_projects, user_can_access_project, user_can_manage_project_users
from apps.audit.services import log_action
from apps.dashboards.services import get_partner_dashboard_metrics, get_project_dashboard_metrics
from apps.projects.models import Company, Project
from apps.projects.serializers import CompanySerializer, ProjectMemberSerializer, ProjectSerializer, ProjectInvitationSerializer
from common.utils import get_project_version, get_user_version, resolve_period


class CompanyViewSet(viewsets.ModelViewSet):
    serializer_class = CompanySerializer

    def get_queryset(self):
        if self.request.user.is_staff:
            return Company.objects.all()
        return Company.objects.filter(projects__in=get_user_projects(self.request.user)).distinct()

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer

    def get_queryset(self):
        return get_user_projects(self.request.user)

    @decorators.action(detail=True, methods=["get"])
    def dashboard(self, request, pk=None):
        project = self.get_object()
        metrics = get_project_dashboard_metrics(request.user, project.pk).copy()
        metrics["project"] = {"id": project.pk, "name": project.name, "project_type": project.project_type}
        metrics.pop("recent_imports", None)
        metrics.pop("recent_transactions", None)
        return response.Response(metrics)

    @decorators.action(detail=True, methods=["get"], url_path="partner-dashboard")
    def partner_dashboard(self, request, pk=None):
        project = self.get_object()
        data = get_partner_dashboard_metrics(request.user, project.pk)
        if data.get("forbidden"):
            return response.Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        data["project"] = {"id": project.pk, "name": project.name, "project_type": project.project_type}
        return response.Response(data)

    @decorators.action(detail=True, methods=["get"], url_path="permissions/me")
    def my_permissions(self, request, pk=None):
        project = self.get_object()
        membership = ProjectMember.objects.filter(project=project, user=request.user, is_active=True).first()
        return response.Response(ProjectMemberSerializer(membership).data if membership else {"role": "owner" if request.user.is_staff else "none"})


class ProjectMemberViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectMemberSerializer

    def get_queryset(self):
        return ProjectMember.objects.filter(project__in=get_user_projects(self.request.user))


class ProjectInvitationViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectInvitationSerializer

    def get_queryset(self):
        return ProjectInvitation.objects.filter(project__in=get_user_projects(self.request.user))

    def perform_create(self, serializer):
        invitation = serializer.save(invited_by=self.request.user)
        log_action(self.request.user, invitation.project, "invite_user", invitation, f"Invited {invitation.email}", request=self.request)


@login_required
def project_list(request):
    return render(request, "projects/list.html", {"projects": get_user_projects(request.user)})


def _project_entry_url(project):
    if project.project_type in [Project.ProjectType.REAL_ESTATE, Project.ProjectType.LEASING]:
        return "real_estate_dashboard"
    if project.project_type == Project.ProjectType.ECOMMERCE:
        return "ecommerce_dashboard"
    if project.project_type == Project.ProjectType.ADS:
        return "ads_dashboard"
    if project.project_type == Project.ProjectType.INVESTMENT:
        return "investments_dashboard"
    return "project_dashboard"


@login_required
def project_select(request):
    projects = get_user_projects(request.user)
    if request.method == "POST":
        project = get_object_or_404(projects, pk=request.POST.get("project"))
        request.session["current_project_id"] = project.pk
        request.session.modified = True
        target = _project_entry_url(project)
        if target == "project_dashboard":
            return redirect(target, pk=project.pk)
        return redirect(target)
    return render(request, "projects/select.html", {"projects": projects})


@login_required
def project_switch(request, pk):
    project = get_object_or_404(get_user_projects(request.user), pk=pk)
    request.session["current_project_id"] = project.pk
    request.session.modified = True
    target = _project_entry_url(project)
    if target == "project_dashboard":
        return redirect(target, pk=project.pk)
    return redirect(target)


@login_required
def project_create(request):
    companies = Company.objects.filter(owner=request.user) if not request.user.is_staff else Company.objects.all()
    if request.method == "POST":
        company_id = request.POST.get("company")
        company = Company.objects.filter(pk=company_id).first() or Company.objects.create(name=request.POST.get("company_name") or "Default Company", owner=request.user)
        project = Project.objects.create(
            company=company,
            name=request.POST["name"],
            project_type=request.POST.get("project_type", "generic"),
            base_currency=request.POST.get("base_currency", "SAR"),
            country=request.POST.get("country", ""),
        )
        ProjectMember.objects.get_or_create(
            user=request.user,
            project=project,
            defaults={"role": "owner", "dashboard_access": "full", "can_view_dashboard": True, "can_view_financials": True, "can_manage_users": True, "can_upload_excel": True, "can_import_data": True},
        )
        log_action(request.user, project, "create_project", project, request=request)
        return redirect("project_detail", pk=project.pk)
    return render(request, "projects/form.html", {"companies": companies})


@login_required
def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not user_can_access_project(request.user, project):
        raise PermissionDenied
    return render(request, "projects/detail.html", {"project": project})


@login_required
def project_dashboard(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not user_can_access_project(request.user, project):
        raise PermissionDenied
    return render(request, "projects/dashboard.html", {"metrics": get_project_dashboard_metrics(request.user, pk), "project": project})


@login_required
def partner_dashboard(request, pk):
    project = get_object_or_404(Project, pk=pk)
    data = get_partner_dashboard_metrics(request.user, pk)
    if data.get("forbidden"):
        raise PermissionDenied
    return render(request, "projects/partner_dashboard.html", {"metrics": data, "project": project})


@login_required
def project_members(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not user_can_manage_project_users(request.user, project):
        raise PermissionDenied
    return render(request, "projects/members.html", {"project": project, "members": project.members.select_related("user")})


@login_required
def member_permissions(request, pk, member_id):
    project = get_object_or_404(Project, pk=pk)
    if not user_can_manage_project_users(request.user, project):
        raise PermissionDenied
    member = get_object_or_404(ProjectMember, pk=member_id, project=project)
    if request.method == "POST":
        bool_fields = [f.name for f in ProjectMember._meta.fields if f.name.startswith("can_")]
        for field in bool_fields:
            setattr(member, field, request.POST.get(field) == "on")
        member.role = request.POST.get("role", member.role)
        member.dashboard_access = request.POST.get("dashboard_access", member.dashboard_access)
        member.save()
        messages.success(request, "تم تحديث الصلاحيات.")
        log_action(request.user, project, "update_permissions", member, request=request)
        return redirect("project_members", pk=project.pk)
    return render(request, "projects/member_permissions.html", {"project": project, "member": member})


@login_required
def project_analytics(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not user_can_access_project(request.user, project):
        raise PermissionDenied

    request.session["current_project_id"] = project.pk
    request.session.modified = True

    period_ctx = resolve_period(request, default="month")

    user_ver = get_user_version(request.user)
    project_ver = get_project_version(project.pk)
    cache_key = f"analytics:project:{request.user.pk}:{project.pk}:{period_ctx['start']}:{period_ctx['end']}:{user_ver}:{project_ver}"
    cached = cache.get(cache_key)
    if cached is not None:
        return render(request, "projects/analytics.html", cached)

    from django.db.models import Sum, Count, Q, Avg
    from apps.finance.models import Transaction
    from apps.imports.models import UploadedFile, ImportBatch, ImportError, RawImportedRow
    from apps.reports.models import Report
    from apps.audit.models import AuditLog
    from apps.integrations.models import ApiConnection, SyncLog, RawApiEvent

    error_messages = []
    start = period_ctx["start"]
    end = period_ctx["end"]
    prev_start = period_ctx["prev_start"]
    prev_end = period_ctx["prev_end"]

    def _pct(curr, prev):
        try:
            c = float(curr or 0)
            p = float(prev or 0)
            if p == 0:
                return None
            return round(((c - p) / p) * 100, 1)
        except Exception:
            return None

    finance = {}
    finance_daily = {"labels": [], "income": [], "expense": []}
    try:
        income_types = [Transaction.TransactionType.INCOME, Transaction.TransactionType.DEPOSIT]
        expense_types = [Transaction.TransactionType.EXPENSE, Transaction.TransactionType.WITHDRAWAL]
        txns = Transaction.objects.filter(project=project, date__range=[start, end])
        prev_txns = Transaction.objects.filter(project=project, date__range=[prev_start, prev_end])

        totals = txns.aggregate(
            income=Sum("amount_base_currency", filter=Q(transaction_type__in=income_types)),
            expense=Sum("amount_base_currency", filter=Q(transaction_type__in=expense_types)),
            count=Count("id"),
        )
        prev_totals = prev_txns.aggregate(
            income=Sum("amount_base_currency", filter=Q(transaction_type__in=income_types)),
            expense=Sum("amount_base_currency", filter=Q(transaction_type__in=expense_types)),
            count=Count("id"),
        )
        income_total = float(totals["income"] or 0)
        expense_total = float(totals["expense"] or 0)
        net_total = income_total - expense_total
        prev_income_total = float(prev_totals["income"] or 0)
        prev_expense_total = float(prev_totals["expense"] or 0)
        prev_net_total = prev_income_total - prev_expense_total

        by_category = list(
            txns.values("transaction_type", "category__name")
            .annotate(total=Sum("amount_base_currency"))
            .order_by("-total")[:12]
        )

        daily_rows = (
            txns.values("date")
            .annotate(
                income=Sum("amount_base_currency", filter=Q(transaction_type__in=income_types)),
                expense=Sum("amount_base_currency", filter=Q(transaction_type__in=expense_types)),
            )
            .order_by("date")
        )
        daily_map = {r["date"]: r for r in daily_rows}
        cursor = start
        while cursor <= end:
            finance_daily["labels"].append(cursor.isoformat())
            r = daily_map.get(cursor)
            finance_daily["income"].append(float((r or {}).get("income") or 0))
            finance_daily["expense"].append(float((r or {}).get("expense") or 0))
            cursor = cursor + timedelta(days=1)

        finance = {
            "income_total": income_total,
            "expense_total": expense_total,
            "net_total": net_total,
            "count": totals["count"] or 0,
            "compare": {
                "income_pct": _pct(income_total, prev_income_total),
                "expense_pct": _pct(expense_total, prev_expense_total),
                "net_pct": _pct(net_total, prev_net_total),
                "count_pct": _pct(totals["count"] or 0, prev_totals["count"] or 0),
            },
            "by_category": [
                {"type": r["transaction_type"], "name": r["category__name"] or "غير مصنف", "amount": float(r["total"] or 0)}
                for r in by_category
            ],
            "recent": list(txns.select_related("account", "category").order_by("-date", "-created_at")[:12]),
        }
    except Exception as exc:
        error_messages.append(f"Finance: {exc}")

    data_ops = {}
    try:
        uploads = UploadedFile.objects.filter(project=project, uploaded_at__date__range=[start, end]).order_by("-uploaded_at")
        batches = ImportBatch.objects.filter(project=project, created_at__date__range=[start, end]).order_by("-created_at")
        raw_rows = RawImportedRow.objects.filter(project=project, created_at__date__range=[start, end])
        import_errors = ImportError.objects.filter(batch__project=project, created_at__date__range=[start, end]).order_by("-created_at")[:30]

        data_ops = {
            "uploads_count": uploads.count(),
            "batches_count": batches.count(),
            "rows_count": raw_rows.count(),
            "errors_count": ImportError.objects.filter(batch__project=project, created_at__date__range=[start, end]).count(),
            "recent_uploads": list(uploads[:10]),
            "recent_batches": list(batches[:10]),
            "recent_errors": list(import_errors),
        }
    except Exception as exc:
        error_messages.append(f"Imports: {exc}")

    reports = {}
    try:
        qs = Report.objects.filter(project=project, created_at__date__range=[start, end]).order_by("-created_at")
        reports = {"count": qs.count(), "recent": list(qs[:10])}
    except Exception as exc:
        error_messages.append(f"Reports: {exc}")

    audit = {}
    try:
        qs = AuditLog.objects.filter(project=project, created_at__date__range=[start, end]).order_by("-created_at")
        by_action = list(qs.values("action").annotate(count=Count("id")).order_by("-count")[:12])
        audit = {"count": qs.count(), "by_action": by_action, "recent": list(qs[:25])}
    except Exception as exc:
        error_messages.append(f"Audit: {exc}")

    integrations = {}
    try:
        connections = ApiConnection.objects.filter(project=project).order_by("-created_at")
        last_connection = connections.first()
        sync_logs = []
        raw_events = []
        if last_connection:
            sync_logs = list(last_connection.sync_logs.filter(started_at__date__range=[start, end]).order_by("-started_at")[:20])
        raw_events = list(RawApiEvent.objects.filter(project=project, received_at__date__range=[start, end]).order_by("-received_at")[:20])
        integrations = {
            "connections": list(connections[:5]),
            "sync_logs": sync_logs,
            "raw_events": raw_events,
        }
    except Exception as exc:
        error_messages.append(f"Integrations: {exc}")

    module = {"type": project.project_type, "kpis": {}, "tables": {}}
    try:
        if project.project_type == Project.ProjectType.ECOMMERCE:
            from apps.ecommerce.models import Order, OrderItem, Product

            paid_statuses = ["SUCCESSFUL", "PAID", "COMPLETED", "successful", "paid"]
            orders = Order.objects.filter(project=project, order_date__range=[start, end])
            prev_orders = Order.objects.filter(project=project, order_date__range=[prev_start, prev_end])

            stats = orders.aggregate(
                sales=Sum("net_total", filter=Q(status__in=paid_statuses)),
                orders=Count("id"),
                abandoned=Count("id", filter=Q(is_abandoned=True)),
                aov=Avg("net_total", filter=Q(status__in=paid_statuses)),
                customers=Count("customer", distinct=True),
            )
            prev_stats = prev_orders.aggregate(
                sales=Sum("net_total", filter=Q(status__in=paid_statuses)),
                orders=Count("id"),
                abandoned=Count("id", filter=Q(is_abandoned=True)),
                aov=Avg("net_total", filter=Q(status__in=paid_statuses)),
                customers=Count("customer", distinct=True),
            )

            top_products = []
            try:
                top_products = list(
                    OrderItem.objects.filter(order__project=project, order__order_date__range=[start, end])
                    .values("product_name")
                    .annotate(qty=Sum("quantity"), revenue=Sum("total_price"))
                    .order_by("-revenue")[:10]
                )
            except Exception:
                top_products = list(Product.objects.filter(project=project).order_by("-stock_quantity").values("name", "stock_quantity")[:10])

            top_customers = list(
                orders.filter(customer__isnull=False)
                .values("customer__name")
                .annotate(total=Sum("net_total"), count=Count("id"))
                .order_by("-total")[:10]
            )

            module["kpis"] = {
                "sales": float(stats["sales"] or 0),
                "orders": stats["orders"] or 0,
                "abandoned": stats["abandoned"] or 0,
                "aov": float(stats["aov"] or 0),
                "customers": stats["customers"] or 0,
                "compare": {
                    "sales_pct": _pct(float(stats["sales"] or 0), float(prev_stats["sales"] or 0)),
                    "orders_pct": _pct(stats["orders"] or 0, prev_stats["orders"] or 0),
                    "abandoned_pct": _pct(stats["abandoned"] or 0, prev_stats["abandoned"] or 0),
                    "aov_pct": _pct(float(stats["aov"] or 0), float(prev_stats["aov"] or 0)),
                },
            }
            module["tables"] = {
                "recent_orders": list(orders.select_related("customer").order_by("-order_date", "-created_at")[:15]),
                "top_products": top_products,
                "top_customers": top_customers,
            }
        elif project.project_type in [Project.ProjectType.REAL_ESTATE, Project.ProjectType.LEASING]:
            from apps.real_estate.models import (
                Property,
                Unit,
                Tenant,
                Lease,
                Collection,
                MaintenanceCost,
                IndustrialUnitRecord,
                IndustrialBuilding,
            )

            props = Property.objects.filter(project=project)
            units = Unit.objects.filter(property__project=project)
            tenants = Tenant.objects.filter(project=project)
            leases = Lease.objects.filter(project=project)
            collections = Collection.objects.filter(lease__project=project, payment_date__range=[start, end])
            costs = MaintenanceCost.objects.filter(property__project=project, date__range=[start, end])

            industrial_units = IndustrialUnitRecord.objects.filter(building__project=project)
            status_rows = list(industrial_units.values("status").annotate(count=Count("id")).order_by("-count")[:10])

            module["kpis"] = {
                "properties": props.count(),
                "units": units.count(),
                "tenants": tenants.count(),
                "leases": leases.count(),
                "collections_sum": float(collections.aggregate(total=Sum("amount"))["total"] or 0),
                "maintenance_sum": float(costs.aggregate(total=Sum("amount"))["total"] or 0),
            }
            module["tables"] = {
                "recent_collections": list(collections.order_by("-payment_date")[:15]),
                "recent_costs": list(costs.order_by("-date")[:15]),
                "industrial_status": status_rows,
                "top_buildings": list(
                    IndustrialBuilding.objects.filter(project=project)
                    .annotate(units_count=Count("unit_records"))
                    .order_by("-units_count")[:10]
                    .values("name", "units_count")
                ),
            }
        elif project.project_type == Project.ProjectType.ADS:
            from apps.ads.models import AdSpendDaily

            rows = AdSpendDaily.objects.filter(project=project, date__range=[start, end])
            totals = rows.aggregate(spend=Sum("spend"), revenue=Sum("revenue"), orders=Sum("orders"), leads=Sum("leads"))
            spend = float(totals["spend"] or 0)
            revenue = float(totals["revenue"] or 0)
            module["kpis"] = {
                "spend": spend,
                "revenue": revenue,
                "roas": round((revenue / spend), 2) if spend else 0,
                "orders": int(totals["orders"] or 0),
                "leads": int(totals["leads"] or 0),
            }
            module["tables"] = {"recent_days": list(rows.order_by("-date")[:20])}
        elif project.project_type == Project.ProjectType.INVESTMENT:
            from apps.investments.models import Asset, InvestmentIncome, InvestmentTransaction

            assets = Asset.objects.filter(project=project)
            incomes = InvestmentIncome.objects.filter(asset__project=project, date__range=[start, end])
            txs = InvestmentTransaction.objects.filter(asset__project=project, date__range=[start, end])
            module["kpis"] = {
                "assets": assets.count(),
                "current_value": float(assets.aggregate(total=Sum("current_value"))["total"] or 0),
                "income_sum": float(incomes.aggregate(total=Sum("amount"))["total"] or 0),
                "tx_sum": float(txs.aggregate(total=Sum("amount"))["total"] or 0),
            }
            module["tables"] = {"recent_income": list(incomes.order_by("-date")[:15]), "recent_txs": list(txs.order_by("-date")[:15])}
    except Exception as exc:
        error_messages.append(f"Module({project.project_type}): {exc}")

    chart_payload = {
        "financeDaily": finance_daily,
        "moduleType": module["type"],
    }

    context = {
        "project": project,
        "projects": get_user_projects(request.user),
        "active": "project_analytics",
        "load_charts": True,
        "period_ctx": period_ctx,
        "errors": error_messages,
        "finance": finance,
        "data_ops": data_ops,
        "reports": reports,
        "audit": audit,
        "integrations": integrations,
        "module": module,
        "chart_payload": json.dumps(chart_payload),
    }
    cache.set(cache_key, context, 60)
    return render(request, "projects/analytics.html", context)
