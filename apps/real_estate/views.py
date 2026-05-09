import json
import hashlib
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rest_framework import viewsets, decorators, response
from apps.accounts.selectors import get_user_projects
from apps.dashboards.services import get_real_estate_metrics
from apps.finance.models import Transaction
from apps.integrations.models import ApiConnection
from apps.integrations.nakhba import DEFAULT_BASE_URL, NAKHBA_PROVIDER, masked_key, sync_nakhba_connection
from apps.projects.models import Project
from apps.real_estate.forms import IndustrialCustomerProfileForm, IndustrialReservationLeadForm, IndustrialUnitRecordForm
from apps.real_estate.models import (
    Collection,
    IndustrialBuilding,
    IndustrialCustomerProfile,
    IndustrialReservationLead,
    IndustrialUnitRecord,
    Installment,
    Lease,
    Property,
    Tenant,
    Unit,
)
from apps.real_estate.serializers import CollectionSerializer, InstallmentSerializer, LeaseSerializer, PropertySerializer, TenantSerializer, UnitSerializer


def _decimal_from_payload(value):
    if value in (None, ""):
        return Decimal("0")
    try:
        return Decimal(str(value).replace(",", "").strip())
    except Exception:
        return Decimal("0")


def _text_from_payload(value):
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _booking_project():
    return Project.objects.filter(industrial_buildings__isnull=False).distinct().first() or Project.objects.first()


class PropertyViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PropertySerializer
    def get_queryset(self):
        return Property.objects.filter(project__in=get_user_projects(self.request.user))


class LeaseViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = LeaseSerializer
    def get_queryset(self):
        return Lease.objects.filter(project__in=get_user_projects(self.request.user))


class CollectionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CollectionSerializer
    def get_queryset(self):
        return Collection.objects.filter(lease__project__in=get_user_projects(self.request.user))


@decorators.api_view(["GET"])
def real_estate_dashboard_api(request):
    project_id = request.query_params.get("project")
    return response.Response(get_real_estate_metrics(request.user, project_id) if project_id else {})


@csrf_exempt
@require_POST
def booking_webhook(request):
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "صيغة JSON غير صحيحة"}, status=400)

    project = _booking_project()
    if not project:
        return JsonResponse({"error": "لا يوجد مشروع متاح لاستقبال الحجز"}, status=404)

    customer = payload.get("customer") or {}
    units = payload.get("units") or []
    if not units:
        return JsonResponse({"error": "لا توجد وحدات في طلب الحجز"}, status=400)

    saved_units = []
    for index, unit_data in enumerate(units, start=1):
        building_number = _text_from_payload(unit_data.get("buildingNumber") or unit_data.get("building_number") or unit_data.get("building"))
        if not building_number:
            return JsonResponse({"error": "رقم المبنى مطلوب لكل وحدة"}, status=400)
        building_name = building_number if building_number.startswith("مبنى") else f"مبنى {building_number}"
        building_type = _text_from_payload(unit_data.get("buildingType") or unit_data.get("building_type") or unit_data.get("activity"))

        building, _ = IndustrialBuilding.objects.get_or_create(
            project=project,
            name=building_name,
            defaults={
                "external_number": int(building_number) if building_number.isdigit() else None,
                "activity": building_type,
                "source_sheet": "N8N webhook",
                "external_payload": unit_data,
            },
        )
        updates = []
        if building_type and not building.activity:
            building.activity = building_type
            updates.append("activity")
        if not building.external_payload:
            building.external_payload = unit_data
            updates.append("external_payload")
        if updates:
            building.save(update_fields=updates)

        unit_number = _text_from_payload(unit_data.get("unitNumber") or unit_data.get("unit_number"))
        if not unit_number:
            return JsonResponse({"error": "رقم الوحدة مطلوب لكل حجز"}, status=400)
        area = _decimal_from_payload(unit_data.get("area"))
        annual_rent = _decimal_from_payload(unit_data.get("price") or unit_data.get("annual_rent") or unit_data.get("rent"))
        rent_per_meter = annual_rent / area if area else Decimal("0")
        unit, _ = IndustrialUnitRecord.objects.update_or_create(
            building=building,
            unit_number=unit_number,
            defaults={
                "sequence": index,
                "unit_type": _text_from_payload(unit_data.get("unitType") or unit_data.get("unit_type")),
                "area": area,
                "activity": _text_from_payload(unit_data.get("activity") or building_type),
                "tenant_name": _text_from_payload(customer.get("fullName") or customer.get("name")),
                "phone": _text_from_payload(customer.get("phone")),
                "rent_per_meter": rent_per_meter,
                "annual_rent": annual_rent,
                "booking_amount": _decimal_from_payload(unit_data.get("bookingAmount") or unit_data.get("booking_amount")),
                "status": IndustrialUnitRecord.Status.RESERVED,
                "raw_data": {"booking": payload, "unit": unit_data},
            },
        )
        saved_units.append({"id": unit.id, "building": building.name, "unit_number": unit.unit_number})

    first_unit = units[0]
    IndustrialReservationLead.objects.update_or_create(
        project=project,
        customer_name=_text_from_payload(customer.get("fullName") or customer.get("name")),
        phone=_text_from_payload(customer.get("phone")),
        building_name=_text_from_payload(first_unit.get("buildingNumber") or first_unit.get("building_number") or first_unit.get("building")),
        unit_number=_text_from_payload(first_unit.get("unitNumber") or first_unit.get("unit_number")),
        defaults={
            "activity": _text_from_payload(customer.get("business")),
            "status": "حجز من N8N",
            "next_step": _text_from_payload(customer.get("notes") or payload.get("message")),
            "raw_data": payload,
        },
    )
    return JsonResponse({"success": True, "units": saved_units}, status=201)


@login_required
def list_page(request, template, context_name, qs):
    return render(request, template, {context_name: qs})


@login_required
def properties_page(request):
    project = _selected_project(request)
    if not project:
        return render(request, "real_estate/properties.html", {"empty_project": True})
    buildings = IndustrialBuilding.objects.filter(project=project).prefetch_related("unit_records").order_by("external_number", "name")
    rows = []
    for building in buildings:
        units = list(building.unit_records.all())
        total = len(units)
        rented = len([unit for unit in units if unit.status == IndustrialUnitRecord.Status.RENTED])
        reserved = len([unit for unit in units if unit.status == IndustrialUnitRecord.Status.RESERVED])
        vacant = len([unit for unit in units if unit.status == IndustrialUnitRecord.Status.VACANT])
        occupied = rented + reserved
        rows.append({
            "building": building,
            "total": total,
            "rented": rented,
            "reserved": reserved,
            "vacant": vacant,
            "occupancy": round((occupied / total) * 100, 1) if total else 0,
            "annual_rent": sum(unit.annual_rent for unit in units),
            "area": sum(unit.area for unit in units),
        })
    return render(request, "real_estate/properties.html", {"project": project, "building_rows": rows})


@login_required
def units_page(request):
    project = _selected_project(request)
    if not project:
        return render(request, "real_estate/units.html", {"empty_project": True})
    units = IndustrialUnitRecord.objects.filter(building__project=project).select_related("building")
    building_id = request.GET.get("building")
    status = request.GET.get("status")
    q = request.GET.get("q", "").strip()
    activity = request.GET.get("activity", "").strip()
    if building_id:
        units = units.filter(building_id=building_id)
    if status:
        units = units.filter(status=status)
    if activity:
        units = units.filter(activity__icontains=activity)
    if q:
        units = units.filter(Q(unit_number__icontains=q) | Q(tenant_name__icontains=q) | Q(phone__icontains=q))
    totals = units.aggregate(count=Count("id"), rent=Sum("annual_rent"), area=Sum("area"))
    return render(request, "real_estate/units.html", {
        "project": project,
        "units": units[:500],
        "buildings": IndustrialBuilding.objects.filter(project=project).order_by("external_number", "name"),
        "status_choices": IndustrialUnitRecord.Status.choices,
        "activities": IndustrialUnitRecord.objects.filter(building__project=project).exclude(activity="").values_list("activity", flat=True).distinct().order_by("activity"),
        "filters": {"building": building_id or "", "status": status or "", "q": q, "activity": activity},
        "totals": totals,
    })

@login_required
def tenants_page(request):
    project = _selected_project(request)
    if not project:
        return render(request, "real_estate/tenants.html", {"empty_project": True})

    tenants = Tenant.objects.filter(project=project)
    q = request.GET.get("q", "").strip()
    if q:
        tenants = tenants.filter(
            Q(name__icontains=q)
            | Q(phone__icontains=q)
            | Q(company_name__icontains=q)
            | Q(activity_type__icontains=q)
        )

    all_units = IndustrialUnitRecord.objects.filter(building__project=project)
    totals = {
        "tenants": tenants.count(),
        "rented_units": all_units.filter(status=IndustrialUnitRecord.Status.RENTED).count(),
        "reserved_units": all_units.filter(status=IndustrialUnitRecord.Status.RESERVED).count(),
        "tenant_units": all_units.exclude(tenant_name="").count(),
    }
    return render(request, "real_estate/tenants.html", {
        "project": project,
        "tenants": tenants[:500],
        "filters": {"q": q},
        "totals": totals,
    })


leases_page = lambda request: list_page(request, "real_estate/leases.html", "leases", Lease.objects.filter(project__in=get_user_projects(request.user))[:100])
collections_page = lambda request: list_page(request, "real_estate/collections.html", "collections", Collection.objects.filter(lease__project__in=get_user_projects(request.user))[:100])
installments_page = lambda request: list_page(request, "real_estate/installments.html", "installments", Installment.objects.filter(project__in=get_user_projects(request.user))[:100])


def _selected_project(request):
    projects = get_user_projects(request.user)
    project_id = request.GET.get("project")
    if not project_id:
        project_id = request.session.get("current_project_id")
    if project_id:
        project = projects.filter(pk=project_id).first()
        if project:
            request.session["current_project_id"] = project.pk
            return project
    return projects.filter(industrial_buildings__isnull=False).distinct().first() or projects.first()

def _nakhba_client(project):
    connection = ApiConnection.objects.filter(project=project, provider=NAKHBA_PROVIDER).order_by("-created_at").first()
    if not connection:
        return None, "لم يتم إعداد ربط نخبة تسكين API لهذا المشروع."
    credentials = connection.credentials or {}
    from apps.integrations.nakhba import NakhbaApiClient
    client = NakhbaApiClient(credentials.get("base_url"), credentials.get("api_key"))
    return client, None

def _is_tenant_accounts_schema_cache_error(message):
    if not message:
        return False
    text = str(message)
    return "tenant_account_units" in text and "schema cache" in text

def _local_tenant_accounts(project, q=""):
    units = IndustrialUnitRecord.objects.filter(building__project=project).exclude(tenant_name="")
    if q:
        units = units.filter(Q(tenant_name__icontains=q) | Q(phone__icontains=q))

    aggregated = (
        units.values("tenant_name", "phone")
        .annotate(units_count=Count("id"), due_total=Sum("remaining_amount"), total_price=Sum("annual_rent"))
        .order_by("tenant_name")
    )

    tenants = list(Tenant.objects.filter(project=project).only("id", "name", "phone", "company_name", "activity_type"))
    by_name = {t.name.strip().lower(): t for t in tenants if t.name}
    by_phone = {t.phone.strip(): t for t in tenants if t.phone}

    accounts = []
    for row in aggregated:
        tenant_name = (row.get("tenant_name") or "").strip()
        phone = (row.get("phone") or "").strip()
        tenant = by_phone.get(phone) or by_name.get(tenant_name.lower())
        local_id = f"local-{tenant.id}" if tenant else ""
        resolved_name = tenant_name or (tenant.name if tenant else "")
        accounts.append({
            "id": local_id,
            "tenant_name": resolved_name,
            "full_name": resolved_name,
            "business_name": tenant.company_name if tenant else "",
            "activity_type": tenant.activity_type if tenant else "",
            "phone": phone or (tenant.phone if tenant else ""),
            "units_count": row.get("units_count") or 0,
            "total_price": row.get("total_price") or 0,
            "remaining_total": row.get("due_total") or 0,
        })
    return accounts

def _local_tenant_account_detail(project, tenant_account_id):
    if not tenant_account_id.startswith("local-"):
        return None
    raw_pk = tenant_account_id.replace("local-", "", 1).strip()
    if not raw_pk.isdigit():
        return None
    tenant = Tenant.objects.filter(project=project, pk=int(raw_pk)).first()
    if not tenant:
        return None

    units_qs = IndustrialUnitRecord.objects.filter(building__project=project, tenant_name=tenant.name).select_related("building")
    if tenant.phone:
        units_qs = units_qs.filter(Q(phone=tenant.phone) | Q(phone=""))

    units = []
    for u in units_qs[:500]:
        units.append({
            "id": u.external_id,
            "unit_id": u.external_id,
            "building_number": u.building.external_number,
            "unit_number": u.unit_number,
            "area": float(u.area or 0),
            "price": float(u.annual_rent or 0),
            "status": u.status,
        })

    totals = units_qs.aggregate(
        total_price=Sum("annual_rent"),
        remaining_total=Sum("remaining_amount"),
        units_count=Count("id"),
    )

    return {
        "id": tenant_account_id,
        "tenant_name": tenant.name,
        "full_name": tenant.name,
        "phone": tenant.phone,
        "email": tenant.email,
        "business_name": tenant.company_name,
        "activity_type": tenant.activity_type,
        "total_price": totals.get("total_price") or 0,
        "remaining_total": totals.get("remaining_total") or 0,
        "units_count": totals.get("units_count") or 0,
        "units": units,
        "invoices": [],
    }

def _normalize_tenant_account_detail(account):
    if not isinstance(account, dict):
        return {"full_name": "", "units": [], "invoices": []}

    full_name = account.get("full_name") or account.get("tenant_name") or account.get("name") or ""
    account["full_name"] = full_name
    account["tenant_name"] = account.get("tenant_name") or full_name
    account["business_name"] = account.get("business_name") or account.get("business") or ""
    account["remaining_total"] = account.get("remaining_total") or account.get("due_total") or 0

    units = account.get("units")
    if not isinstance(units, list):
        units = []
        tenant_units = account.get("tenant_account_units")
        if isinstance(tenant_units, list):
            for row in tenant_units:
                if not isinstance(row, dict):
                    continue
                unit_id = row.get("unit_id") or row.get("id")
                inner = row.get("units") if isinstance(row.get("units"), dict) else {}
                units.append({
                    "id": unit_id,
                    "unit_id": unit_id,
                    "building_number": inner.get("building_number"),
                    "unit_number": inner.get("unit_number"),
                    "area": inner.get("area"),
                    "price": inner.get("price"),
                    "status": inner.get("status"),
                    "activity": inner.get("activity"),
                    "unit_type": inner.get("unit_type"),
                })
    account["units"] = units
    account["units_count"] = account.get("units_count") or len(units)
    if "invoices" not in account or not isinstance(account.get("invoices"), list):
        account["invoices"] = []
    return account


def _status_label(status):
    return dict(IndustrialUnitRecord.Status.choices).get(status, status)


def _float(value):
    return float(value or 0)


@login_required
def dashboard_page(request):
    project = _selected_project(request)
    if not project:
        return render(request, "real_estate/dashboard.html", {"empty_project": True})
    request.session["current_project_id"] = project.pk

    units = IndustrialUnitRecord.objects.filter(building__project=project).select_related("building")
    building_id = request.GET.get("building")
    status = request.GET.get("status")
    q = request.GET.get("q", "").strip()
    if building_id:
        units = units.filter(building_id=building_id)
    if status:
        units = units.filter(status=status)
    if q:
        units = units.filter(Q(tenant_name__icontains=q) | Q(unit_number__icontains=q) | Q(phone__icontains=q))

    all_units = IndustrialUnitRecord.objects.filter(building__project=project).select_related("building")
    totals = all_units.aggregate(
        total_units=Count("id"),
        total_area=Sum("area"),
        expected_rent=Sum("annual_rent"),
        booking_total=Sum("booking_amount"),
        paid_total=Sum("paid_amount"),
        remaining_total=Sum("remaining_amount"),
    )
    status_counts = {row["status"]: row["count"] for row in all_units.values("status").annotate(count=Count("id"))}
    rented = status_counts.get(IndustrialUnitRecord.Status.RENTED, 0)
    reserved = status_counts.get(IndustrialUnitRecord.Status.RESERVED, 0)
    vacant = status_counts.get(IndustrialUnitRecord.Status.VACANT, 0)
    total_units = totals["total_units"] or 0
    occupancy_rate = round(((rented + reserved) / total_units) * 100, 1) if total_units else 0
    target_rate = 40
    target_gap = round(occupancy_rate - target_rate, 1)
    expected_rent = totals["expected_rent"] or Decimal("0")
    paid_total = totals["paid_total"] or Decimal("0")
    total_area = totals["total_area"] or Decimal("0")
    collection_rate = round(float((paid_total / expected_rent) * 100), 1) if expected_rent else 0
    average_meter_rate = round(float(expected_rent / total_area), 1) if total_area else 0

    building_rows = []
    for building in IndustrialBuilding.objects.filter(project=project).prefetch_related("unit_records"):
        records = list(building.unit_records.all())
        count = len(records)
        occupied = len([unit for unit in records if unit.status in [IndustrialUnitRecord.Status.RENTED, IndustrialUnitRecord.Status.RESERVED]])
        building_rows.append({
            "id": building.id,
            "name": building.name,
            "activity": building.activity,
            "units": count,
            "rented": len([unit for unit in records if unit.status == IndustrialUnitRecord.Status.RENTED]),
            "reserved": len([unit for unit in records if unit.status == IndustrialUnitRecord.Status.RESERVED]),
            "vacant": len([unit for unit in records if unit.status == IndustrialUnitRecord.Status.VACANT]),
            "occupancy": round((occupied / count) * 100, 1) if count else 0,
            "annual_rent": float(sum(unit.annual_rent for unit in records)),
            "paid": float(sum(unit.paid_amount for unit in records)),
            "remaining": float(sum(unit.remaining_amount for unit in records)),
        })
    top_buildings = sorted(building_rows, key=lambda row: row["occupancy"], reverse=True)[:3]
    attention_buildings = sorted(building_rows, key=lambda row: row["occupancy"])[:3]
    activity_rows = []
    for row in all_units.values("activity").annotate(units=Count("id"), rent=Sum("annual_rent"), area=Sum("area")).order_by("-units"):
        activity_rows.append({
            "activity": row["activity"] or "غير محدد",
            "units": row["units"],
            "rent": _float(row["rent"]),
            "area": _float(row["area"]),
        })

    chart_payload = {
        "status": {
            "labels": [_status_label(IndustrialUnitRecord.Status.RENTED), _status_label(IndustrialUnitRecord.Status.RESERVED), _status_label(IndustrialUnitRecord.Status.VACANT)],
            "values": [rented, reserved, vacant],
        },
        "buildings": {
            "labels": [row["name"] for row in building_rows],
            "occupancy": [row["occupancy"] for row in building_rows],
            "annualRent": [row["annual_rent"] for row in building_rows],
        },
        "activity": {
            "labels": [row["activity"] for row in activity_rows],
            "units": [row["units"] for row in activity_rows],
            "rent": [row["rent"] for row in activity_rows],
        },
    }

    context = {
        "project": project,
        "projects": get_user_projects(request.user),
        "load_charts": True,
        "buildings": IndustrialBuilding.objects.filter(project=project),
        "building_rows": building_rows,
        "units": units[:250],
        "leads": IndustrialReservationLead.objects.filter(project=project)[:20],
        "customers": IndustrialCustomerProfile.objects.filter(project=project)[:20],
        "status_choices": IndustrialUnitRecord.Status.choices,
        "filters": {"building": building_id or "", "status": status or "", "q": q},
        "totals": totals,
        "rented": rented,
        "reserved": reserved,
        "vacant": vacant,
        "occupancy_rate": occupancy_rate,
        "target_rate": target_rate,
        "target_gap": target_gap,
        "collection_rate": collection_rate,
        "average_meter_rate": average_meter_rate,
        "top_buildings": top_buildings,
        "attention_buildings": attention_buildings,
        "activity_rows": activity_rows,
        "chart_payload": json.dumps(chart_payload, cls=DjangoJSONEncoder),
        "api_connection": ApiConnection.objects.filter(project=project, provider=NAKHBA_PROVIDER).order_by("-created_at").first(),
    }
    return render(request, "real_estate/dashboard.html", context)

def _resolve_period(request):
    today = timezone.localdate()
    period = (request.GET.get("period") or "month").strip()
    year = (request.GET.get("year") or "").strip()
    month = (request.GET.get("month") or "").strip()
    start_raw = (request.GET.get("start") or "").strip()
    end_raw = (request.GET.get("end") or "").strip()

    def _safe_int(value, default):
        try:
            return int(value)
        except Exception:
            return default

    if period == "today":
        start_date = end_date = today
    elif period == "year":
        y = _safe_int(year, today.year)
        start_date = date(y, 1, 1)
        end_date = date(y, 12, 31)
    elif period == "month":
        y = _safe_int(year, today.year)
        m = _safe_int(month, today.month)
        m = min(max(m, 1), 12)
        start_date = date(y, m, 1)
        end_date = (date(y + 1, 1, 1) - timedelta(days=1)) if m == 12 else (date(y, m + 1, 1) - timedelta(days=1))
    elif period == "custom":
        try:
            start_date = date.fromisoformat(start_raw) if start_raw else today.replace(day=1)
        except Exception:
            start_date = today.replace(day=1)
        try:
            end_date = date.fromisoformat(end_raw) if end_raw else today
        except Exception:
            end_date = today
        if end_date < start_date:
            start_date, end_date = end_date, start_date
    else:
        period = "month"
        start_date = today.replace(day=1)
        end_date = today

    naive_start = datetime.combine(start_date, time.min)
    naive_end = datetime.combine(end_date + timedelta(days=1), time.min)
    if timezone.is_aware(timezone.now()):
        start_dt = timezone.make_aware(naive_start)
        end_dt = timezone.make_aware(naive_end)
    else:
        start_dt = naive_start
        end_dt = naive_end

    return {
        "period": period,
        "year": _safe_int(year, today.year),
        "month": _safe_int(month, today.month),
        "start_date": start_date,
        "end_date": end_date,
        "start_dt": start_dt,
        "end_dt": end_dt,
    }

@login_required
def analytics_page(request):
    project = _selected_project(request)
    if not project:
        return render(request, "real_estate/analytics.html", {"empty_project": True})

    request.session["current_project_id"] = project.pk
    period_ctx = _resolve_period(request)
    start_date = period_ctx["start_date"]
    end_date = period_ctx["end_date"]
    start_dt = period_ctx["start_dt"]
    end_dt = period_ctx["end_dt"]

    txns = (
        Transaction.objects.filter(project=project, date__range=[start_date, end_date])
        .select_related("account", "category")
        .order_by("-date", "-created_at")
    )
    income_types = [Transaction.TransactionType.INCOME, Transaction.TransactionType.DEPOSIT]
    expense_types = [Transaction.TransactionType.EXPENSE, Transaction.TransactionType.WITHDRAWAL]

    finance_totals = txns.aggregate(
        income=Sum("amount_base_currency", filter=Q(transaction_type__in=income_types)),
        expense=Sum("amount_base_currency", filter=Q(transaction_type__in=expense_types)),
        count=Count("id"),
    )
    income_total = finance_totals["income"] or Decimal("0")
    expense_total = finance_totals["expense"] or Decimal("0")

    category_rows = (
        txns.values("transaction_type", "category__name")
        .annotate(total=Sum("amount_base_currency"))
        .order_by("-total")[:15]
    )
    finance_by_category = [
        {"type": row["transaction_type"], "name": row["category__name"] or "غير مصنف", "amount": float(row["total"] or 0)}
        for row in category_rows
    ]

    daily_rows = (
        txns.values("date")
        .annotate(
            income=Sum("amount_base_currency", filter=Q(transaction_type__in=income_types)),
            expense=Sum("amount_base_currency", filter=Q(transaction_type__in=expense_types)),
        )
        .order_by("date")
    )
    finance_by_day = {row["date"]: {"income": float(row["income"] or 0), "expense": float(row["expense"] or 0)} for row in daily_rows}
    days = []
    cursor = start_date
    while cursor <= end_date:
        days.append(cursor)
        cursor += timedelta(days=1)
    finance_daily = [
        {"date": d.isoformat(), "income": finance_by_day.get(d, {}).get("income", 0), "expense": finance_by_day.get(d, {}).get("expense", 0)}
        for d in days
    ]

    all_units = IndustrialUnitRecord.objects.filter(building__project=project).select_related("building")
    units_totals = all_units.aggregate(
        units=Count("id"),
        area=Sum("area"),
        expected=Sum("annual_rent"),
        paid=Sum("paid_amount"),
        remaining=Sum("remaining_amount"),
    )
    status_counts = {row["status"]: row["count"] for row in all_units.values("status").annotate(count=Count("id"))}
    rented = status_counts.get(IndustrialUnitRecord.Status.RENTED, 0)
    reserved = status_counts.get(IndustrialUnitRecord.Status.RESERVED, 0)
    vacant = status_counts.get(IndustrialUnitRecord.Status.VACANT, 0)
    total_units = units_totals["units"] or 0
    occupancy_rate = round(((rented + reserved) / total_units) * 100, 1) if total_units else 0

    expected_total = units_totals["expected"] or Decimal("0")
    paid_total = units_totals["paid"] or Decimal("0")
    collection_rate = round(float((paid_total / expected_total) * 100), 1) if expected_total else 0

    unit_updates = all_units.filter(updated_at__gte=start_dt, updated_at__lt=end_dt).count()
    building_updates = IndustrialBuilding.objects.filter(project=project, updated_at__gte=start_dt, updated_at__lt=end_dt).count()

    leads = IndustrialReservationLead.objects.filter(project=project, created_at__gte=start_dt, created_at__lt=end_dt)
    customers = IndustrialCustomerProfile.objects.filter(project=project, created_at__gte=start_dt, created_at__lt=end_dt)

    leads_daily = (
        leads.annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )
    customers_daily = (
        customers.annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )
    leads_by_day = {row["day"]: row["count"] for row in leads_daily}
    customers_by_day = {row["day"]: row["count"] for row in customers_daily}

    api_connection = ApiConnection.objects.filter(project=project, provider=NAKHBA_PROVIDER).order_by("-created_at").first()
    raw_events = project.raw_api_events.filter(provider=NAKHBA_PROVIDER, received_at__gte=start_dt, received_at__lt=end_dt)
    sync_logs = []
    if api_connection:
        sync_logs = list(api_connection.sync_logs.filter(started_at__gte=start_dt, started_at__lt=end_dt).order_by("-started_at")[:20])

    chart_payload = {
        "financeDaily": {
            "labels": [row["date"] for row in finance_daily],
            "income": [row["income"] for row in finance_daily],
            "expense": [row["expense"] for row in finance_daily],
        },
        "unitStatus": {
            "labels": [_status_label(IndustrialUnitRecord.Status.RENTED), _status_label(IndustrialUnitRecord.Status.RESERVED), _status_label(IndustrialUnitRecord.Status.VACANT)],
            "values": [rented, reserved, vacant],
        },
        "growth": {
            "labels": [d.isoformat() for d in days],
            "leads": [leads_by_day.get(d, 0) for d in days],
            "customers": [customers_by_day.get(d, 0) for d in days],
        },
    }

    context = {
        "project": project,
        "projects": get_user_projects(request.user),
        "load_charts": True,
        "period_ctx": period_ctx,
        "finance": {
            "income_total": float(income_total),
            "expense_total": float(expense_total),
            "net_total": float(income_total - expense_total),
            "count": finance_totals["count"] or 0,
            "by_category": finance_by_category,
            "recent": [
                {
                    "date": str(t.date),
                    "type": t.transaction_type,
                    "amount": float(t.amount_base_currency),
                    "desc": t.description or "",
                    "category": (t.category.name if t.category else "غير مصنف"),
                }
                for t in txns[:25]
            ],
        },
        "real_estate": {
            "total_units": total_units,
            "rented": rented,
            "reserved": reserved,
            "vacant": vacant,
            "occupancy_rate": occupancy_rate,
            "expected_total": float(expected_total),
            "paid_total": float(paid_total),
            "remaining_total": float(units_totals["remaining"] or 0),
            "total_area": float(units_totals["area"] or 0),
            "collection_rate": collection_rate,
            "buildings_count": IndustrialBuilding.objects.filter(project=project).count(),
            "unit_updates": unit_updates,
            "building_updates": building_updates,
        },
        "growth": {
            "leads_count": leads.count(),
            "customers_count": customers.count(),
            "recent_leads": list(leads.order_by("-created_at").values("customer_name", "phone", "activity", "status", "created_at")[:10]),
            "recent_customers": list(customers.order_by("-created_at").values("customer_name", "phone", "activity", "relationship_status", "created_at")[:10]),
        },
        "api": {
            "connection": api_connection,
            "raw_events_count": raw_events.count(),
            "raw_events": list(raw_events.order_by("-received_at").values("endpoint", "received_at")[:15]),
            "sync_logs": sync_logs,
        },
        "chart_payload": json.dumps(chart_payload, cls=DjangoJSONEncoder),
    }
    return render(request, "real_estate/analytics.html", context)


@login_required
def bookings_page(request):
    project = _selected_project(request)
    if not project:
        return redirect("project_select")
    
    status = request.GET.get("status", "")
    
    bookings_data = []
    error_message = None
    client, error = _nakhba_client(project)
    if error:
        error_message = error

    if request.method == "POST" and client:
        action = request.POST.get("action")
        booking_id = request.POST.get("booking_id")
        if action in {"confirm", "cancel"} and booking_id:
            try:
                client.update_booking(booking_id, {"status": "confirmed" if action == "confirm" else "cancelled"})
                messages.success(request, "تم تحديث حالة الحجز.")
            except Exception as exc:
                messages.error(request, f"فشل تحديث الحجز: {exc}")
        return redirect("real_estate_bookings")

    if client:
        try:
            params = {}
            if status:
                params["status"] = status
            response = client.bookings(params=params)
            bookings_data = response.get("data", [])
        except Exception as e:
            error_message = str(e)
    
    return render(request, "real_estate/bookings.html", {
        "project": project,
        "bookings": bookings_data,
        "status_filter": status,
        "error_message": error_message,
    })

@login_required
def customers_page(request):
    project = _selected_project(request)
    if not project:
        return redirect("project_select")

    q = request.GET.get("q", "").strip()
    customers_data = []
    error_message = None

    client, error = _nakhba_client(project)
    if error:
        error_message = error
    elif client:
        try:
            params = {}
            if q:
                params["search"] = q
            response = client.customers(params=params)
            customers_data = response.get("data", [])
        except Exception as exc:
            error_message = str(exc)

    return render(request, "real_estate/customers.html", {
        "project": project,
        "customers": customers_data,
        "filters": {"q": q},
        "error_message": error_message,
    })

@login_required
def customer_detail_page(request, user_id):
    project = _selected_project(request)
    if not project:
        return redirect("project_select")

    customer_data = None
    error_message = None
    client, error = _nakhba_client(project)
    if error:
        error_message = error
    elif client:
        try:
            payload = client.customer_detail(user_id)
            customer_data = payload.get("data") if isinstance(payload, dict) and "data" in payload else payload
        except Exception as exc:
            error_message = str(exc)

    return render(request, "real_estate/customer_detail.html", {
        "project": project,
        "customer": customer_data,
        "user_id": user_id,
        "error_message": error_message,
    })

@login_required
def audit_log_page(request):
    project = _selected_project(request)
    if not project:
        return redirect("project_select")

    table = request.GET.get("table", "").strip()
    action = request.GET.get("action", "").strip()
    user_id = request.GET.get("user_id", "").strip()
    limit = request.GET.get("limit", "").strip()

    audit_rows = []
    error_message = None

    client, error = _nakhba_client(project)
    if error:
        error_message = error
    elif client:
        try:
            params = {}
            if table:
                params["table"] = table
            if action:
                params["action"] = action
            if user_id:
                params["user_id"] = user_id
            if limit:
                params["limit"] = limit
            response = client.audit_log(params=params)
            audit_rows = response.get("data", [])
        except Exception as exc:
            error_message = str(exc)

    return render(request, "real_estate/audit_log.html", {
        "project": project,
        "rows": audit_rows,
        "filters": {"table": table, "action": action, "user_id": user_id, "limit": limit},
        "error_message": error_message,
    })

@login_required
def tenant_accounts_page(request):
    project = _selected_project(request)
    if not project:
        return redirect("project_select")

    q = request.GET.get("q", "").strip()
    accounts = []
    error_message = None
    fallback_mode = False
    fallback_reason = ""

    client, error = _nakhba_client(project)
    if error:
        error_message = error
    elif client:
        try:
            params = {}
            if q:
                params["search"] = q
            response = client.tenant_accounts(params=params)
            accounts = response.get("data", [])
        except Exception as exc:
            if _is_tenant_accounts_schema_cache_error(exc):
                fallback_mode = True
                fallback_reason = "API/tenant-accounts فيه مشكلة في علاقة الجداول داخل Supabase. تم عرض بديل محلي من بيانات المشروع."
                accounts = _local_tenant_accounts(project, q=q)
            else:
                error_message = str(exc)

    return render(request, "real_estate/tenant_accounts.html", {
        "project": project,
        "accounts": accounts,
        "filters": {"q": q},
        "error_message": error_message,
        "fallback_mode": fallback_mode,
        "fallback_reason": fallback_reason,
    })

@login_required
def tenant_account_detail_page(request, tenant_account_id):
    project = _selected_project(request)
    if not project:
        return redirect("project_select")

    if tenant_account_id.startswith("local-"):
        account = _local_tenant_account_detail(project, tenant_account_id)
        return render(request, "real_estate/tenant_account_detail.html", {
            "project": project,
            "account": account,
            "tenant_account_id": tenant_account_id,
            "error_message": None if account else "لا يمكن عرض هذا الحساب المحلي.",
            "is_local": True,
        })

    client, error = _nakhba_client(project)
    if error:
        return render(request, "real_estate/tenant_account_detail.html", {
            "project": project,
            "account": None,
            "tenant_account_id": tenant_account_id,
            "error_message": error,
            "is_local": False,
        })

    if request.method == "POST":
        action = request.POST.get("action")
        try:
            if action == "add_units":
                raw_ids = request.POST.get("unit_ids", "")
                unit_ids = [x.strip() for x in raw_ids.replace("\n", ",").split(",") if x.strip()]
                if unit_ids:
                    client.tenant_account_add_units(tenant_account_id, unit_ids)
                    messages.success(request, "تم ربط الوحدات بحساب المستأجر.")
            elif action == "remove_unit":
                unit_id = request.POST.get("unit_id", "").strip()
                if unit_id:
                    client.tenant_account_remove_unit(tenant_account_id, unit_id)
                    messages.success(request, "تم إزالة الوحدة من حساب المستأجر.")
        except Exception as exc:
            messages.error(request, f"فشل تنفيذ العملية: {exc}")
        return redirect("real_estate_tenant_account_detail", tenant_account_id=tenant_account_id)

    account = None
    error_message = None
    try:
        payload = client.tenant_account_detail(tenant_account_id)
        account = payload.get("data") if isinstance(payload, dict) and "data" in payload else payload
        account = _normalize_tenant_account_detail(account)
    except Exception as exc:
        error_message = str(exc)

    return render(request, "real_estate/tenant_account_detail.html", {
        "project": project,
        "account": account,
        "tenant_account_id": tenant_account_id,
        "error_message": error_message,
        "is_local": False,
    })

@login_required
def invoices_page(request):
    project = _selected_project(request)
    if not project:
        return redirect("project_select")

    tenant_account_id = request.GET.get("tenant_account_id", "").strip()
    paid = request.GET.get("paid", "").strip()

    invoices = []
    error_message = None

    client, error = _nakhba_client(project)
    if error:
        error_message = error
    elif client:
        try:
            params = {}
            if tenant_account_id:
                params["tenant_account_id"] = tenant_account_id
            if paid in {"true", "false"}:
                params["paid"] = paid
            response = client.invoices(params=params)
            invoices = response.get("data", [])
        except Exception as exc:
            error_message = str(exc)

    return render(request, "real_estate/invoices.html", {
        "project": project,
        "invoices": invoices,
        "filters": {"tenant_account_id": tenant_account_id, "paid": paid},
        "error_message": error_message,
    })


@login_required
def users_page(request):
    project = _selected_project(request)
    if not project:
        return redirect("project_select")
    
    users_data = []
    error_message = None
    
    client, error = _nakhba_client(project)
    if error:
        error_message = error
    elif client:
        try:
            response = client.users()
            users_data = response.get("data", [])
        except Exception as e:
            error_message = str(e)
    
    return render(request, "real_estate/users.html", {
        "project": project,
        "users": users_data,
        "error_message": error_message,
    })


@login_required
def nakhba_api_docs(request):
    project = _selected_project(request)
    if not project:
        return redirect("project_select")
    return render(request, "real_estate/nakhba_api_docs.html", {
        "project": project,
        "base_url": DEFAULT_BASE_URL,
    })


@login_required
def nakhba_api_settings(request):
    project = _selected_project(request)
    if not project:
        return redirect("project_select")
    connection, _ = ApiConnection.objects.get_or_create(
        project=project,
        provider=NAKHBA_PROVIDER,
        defaults={
            "name": "نخبة تسكين API",
            "credentials": {"base_url": DEFAULT_BASE_URL},
            "created_by": request.user,
        },
    )
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "save":
            credentials = connection.credentials or {}
            api_key = request.POST.get("api_key", "").strip()
            credentials["base_url"] = request.POST.get("base_url", DEFAULT_BASE_URL).strip() or DEFAULT_BASE_URL
            if api_key:
                credentials["api_key"] = api_key
            connection.credentials = credentials
            connection.status = "configured" if credentials.get("api_key") else "missing_key"
            connection.name = request.POST.get("name", connection.name).strip() or connection.name
            connection.save(update_fields=["credentials", "status", "name"])
            messages.success(request, "تم حفظ إعدادات API.")
            return redirect("nakhba_api_settings")
        if action == "sync":
            try:
                sync_log = sync_nakhba_connection(connection)
                messages.success(request, f"تمت المزامنة: {sync_log.records_fetched} سجل، إنشاء {sync_log.records_created}، تحديث {sync_log.records_updated}.")
            except Exception as exc:
                messages.error(request, f"فشلت المزامنة: {exc}")
            return redirect("nakhba_api_settings")
    credentials = connection.credentials or {}
    return render(request, "real_estate/nakhba_api_settings.html", {
        "project": project,
        "connection": connection,
        "base_url": credentials.get("base_url") or DEFAULT_BASE_URL,
        "masked_api_key": masked_key(credentials.get("api_key", "")),
        "sync_logs": connection.sync_logs.order_by("-started_at")[:8],
    })


@login_required
def industrial_unit_edit(request, pk):
    unit = get_object_or_404(IndustrialUnitRecord.objects.select_related("building", "building__project"), pk=pk, building__project__in=get_user_projects(request.user))
    form = IndustrialUnitRecordForm(request.POST or None, instance=unit)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "تم حفظ بيانات الوحدة.")
        return redirect("real_estate_dashboard")
    return render(request, "real_estate/industrial_form.html", {"form": form, "title": f"تعديل الوحدة {unit.unit_number}", "project": unit.building.project})


@login_required
def industrial_lead_edit(request, pk):
    lead = get_object_or_404(IndustrialReservationLead, pk=pk, project__in=get_user_projects(request.user))
    form = IndustrialReservationLeadForm(request.POST or None, instance=lead)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "تم حفظ بيانات الاستفسار.")
        return redirect("real_estate_dashboard")
    return render(request, "real_estate/industrial_form.html", {"form": form, "title": f"تعديل الاستفسار: {lead.customer_name}", "project": lead.project})


@login_required
def industrial_customer_edit(request, pk):
    customer = get_object_or_404(IndustrialCustomerProfile, pk=pk, project__in=get_user_projects(request.user))
    form = IndustrialCustomerProfileForm(request.POST or None, instance=customer)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "تم حفظ بيانات العميل.")
        return redirect("real_estate_dashboard")
    return render(request, "real_estate/industrial_form.html", {"form": form, "title": f"تعديل العميل: {customer.customer_name}", "project": customer.project})
