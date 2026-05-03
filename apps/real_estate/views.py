import json
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Count, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rest_framework import viewsets, decorators, response
from apps.accounts.selectors import get_user_projects
from apps.dashboards.services import get_real_estate_metrics
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
