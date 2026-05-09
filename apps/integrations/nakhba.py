from decimal import Decimal, InvalidOperation
import json
import hashlib
from datetime import date
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.db import transaction
from django.core.cache import cache
from django.utils import timezone

from apps.integrations.models import RawApiEvent, SyncLog
from apps.real_estate.models import IndustrialBuilding, IndustrialUnitRecord, Tenant


NAKHBA_PROVIDER = "nakhba_taskin"
DEFAULT_BASE_URL = "https://wqzseofoerwevfebguse.supabase.co/functions/v1/api"


class NakhbaApiError(Exception):
    pass


class NakhbaApiClient:
    def __init__(self, base_url=DEFAULT_BASE_URL, api_key="", timeout=90):
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def stats(self):
        return self.request("stats")

    def buildings(self):
        return self.request("buildings")

    def building_detail(self, number):
        return self.request(f"buildings/{number}")

    def units(self, params=None):
        return self.request("units", params=params)

    def unit_detail(self, unit_id):
        return self.request(f"units/{unit_id}")

    def create_unit(self, data):
        return self.request("units", method="POST", data=data)

    def update_unit(self, unit_id, data):
        return self.request(f"units/{unit_id}", method="PATCH", data=data)

    def delete_unit(self, unit_id):
        return self.request(f"units/{unit_id}", method="DELETE")

    def create_booking(self, data):
        return self.request("bookings", method="POST", data=data)

    def tenants(self, params=None):
        return self.request("tenants", params=params)

    def create_tenant(self, data):
        return self.request("tenants", method="POST", data=data)

    def update_tenant(self, tenant_id, data):
        return self.request(f"tenants/{tenant_id}", method="PATCH", data=data)

    def delete_tenant(self, tenant_id):
        return self.request(f"tenants/{tenant_id}", method="DELETE")

    def bookings(self, params=None):
        return self.request("bookings", params=params)

    def booking_detail(self, booking_id):
        return self.request(f"bookings/{booking_id}")

    def update_booking(self, booking_id, data):
        return self.request(f"bookings/{booking_id}", method="PATCH", data=data)

    def customers(self, params=None):
        return self.request("customers", params=params)

    def customer_detail(self, user_id):
        return self.request(f"customers/{user_id}")

    def users(self):
        return self.request("users")

    def audit_log(self, params=None):
        return self.request("audit-log", params=params)

    def tenant_accounts(self, params=None):
        return self.request("tenant-accounts", params=params)

    def tenant_account_detail(self, tenant_account_id):
        return self.request(f"tenant-accounts/{tenant_account_id}")

    def tenant_account_add_units(self, tenant_account_id, unit_ids):
        return self.request(f"tenant-accounts/{tenant_account_id}/units", method="POST", data={"unit_ids": unit_ids})

    def tenant_account_remove_unit(self, tenant_account_id, unit_id):
        return self.request(f"tenant-accounts/{tenant_account_id}/units/{unit_id}", method="DELETE")

    def invoices(self, params=None):
        return self.request("invoices", params=params)

    def request(self, path, params=None, method="GET", data=None):
        if not self.api_key:
            raise NakhbaApiError("مفتاح API غير مسجل.")
        url = f"{self.base_url}/{path.lstrip('/')}"
        if params:
            url = f"{url}?{urlencode(params)}"
        
        headers = {
            "X-API-Key": self.api_key, 
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        cache_key = None
        if method == "GET":
            key_material = json.dumps(
                {"base_url": self.base_url, "path": path, "params": params or {}, "api": hashlib.sha256(self.api_key.encode("utf-8")).hexdigest()[:16]},
                sort_keys=True,
                ensure_ascii=False,
            ).encode("utf-8")
            cache_key = f"nakhba:get:{hashlib.sha256(key_material).hexdigest()}"
            cached = cache.get(cache_key)
            if cached is not None:
                return cached

        body_data = None
        if data:
            body_data = json.dumps(data).encode("utf-8")

        request = Request(url, headers=headers, method=method, data=body_data)
        try:
            with urlopen(request, timeout=self.timeout) as response:
                body = response.read().decode("utf-8")
                payload = json.loads(body) if body else {}
                if cache_key:
                    cache.set(cache_key, payload, 30)
                return payload
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise NakhbaApiError(f"API error {exc.code}: {detail or exc.reason}") from exc
        except (URLError, TimeoutError) as exc:
            raise NakhbaApiError(f"فشل الاتصال بالـ API: {exc}") from exc


def masked_key(api_key):
    if not api_key:
        return ""
    if len(api_key) <= 10:
        return "********"
    return f"{api_key[:8]}...{api_key[-4:]}"


def sync_nakhba_connection(api_connection):
    credentials = api_connection.credentials or {}
    client = NakhbaApiClient(
        base_url=credentials.get("base_url") or DEFAULT_BASE_URL,
        api_key=credentials.get("api_key") or "",
        timeout=int(credentials.get("timeout") or 90),
    )
    sync_log = SyncLog.objects.create(api_connection=api_connection, status="running")
    fetched = created = updated = 0
    try:
        buildings_payload = client.buildings()
        units_payload = client.units()
        tenants_payload = client.tenants()
        stats_payload = {}
        try:
            stats_payload = client.stats()
        except NakhbaApiError:
            stats_payload = {}

        RawApiEvent.objects.create(project=api_connection.project, provider=NAKHBA_PROVIDER, endpoint="/buildings", payload=buildings_payload)
        RawApiEvent.objects.create(project=api_connection.project, provider=NAKHBA_PROVIDER, endpoint="/units", payload=units_payload)
        RawApiEvent.objects.create(project=api_connection.project, provider=NAKHBA_PROVIDER, endpoint="/tenants", payload=tenants_payload)
        if stats_payload:
            RawApiEvent.objects.create(project=api_connection.project, provider=NAKHBA_PROVIDER, endpoint="/stats", payload=stats_payload)

        building_rows = buildings_payload.get("data", [])
        unit_rows = units_payload.get("data", [])
        tenant_rows = tenants_payload.get("data", [])
        fetched = len(building_rows) + len(unit_rows) + len(tenant_rows)

        with transaction.atomic():
            created, updated = _sync_buildings(api_connection.project, building_rows)
            unit_created, unit_updated = _sync_units(api_connection.project, unit_rows)
            tenant_created, tenant_updated = _sync_tenants(api_connection.project, tenant_rows)
            created += unit_created
            updated += unit_updated
            created += tenant_created
            updated += tenant_updated
            api_connection.status = "active"
            api_connection.last_sync_at = timezone.now()
            api_connection.save(update_fields=["status", "last_sync_at"])

        sync_log.status = "completed"
        sync_log.finished_at = timezone.now()
        sync_log.records_fetched = fetched
        sync_log.records_created = created
        sync_log.records_updated = updated
        sync_log.save(update_fields=["status", "finished_at", "records_fetched", "records_created", "records_updated"])
        return sync_log
    except Exception as exc:
        api_connection.status = "failed"
        api_connection.save(update_fields=["status"])
        sync_log.status = "failed"
        sync_log.finished_at = timezone.now()
        sync_log.records_fetched = fetched
        sync_log.records_created = created
        sync_log.records_updated = updated
        sync_log.error_message = str(exc)
        sync_log.save(update_fields=["status", "finished_at", "records_fetched", "records_created", "records_updated", "error_message"])
        raise


def _sync_buildings(project, rows):
    created = updated = 0
    for row in rows:
        number = _int(row.get("number"))
        if not number:
            continue
        _, was_created = _get_or_update_building(project, number, row)
        if was_created:
            created += 1
        else:
            updated += 1
    return created, updated


def _get_or_update_building(project, number, payload=None):
    payload = payload or {}
    name = f"مبنى {number}"
    building = (
        IndustrialBuilding.objects.filter(project=project, external_number=number).first()
        or IndustrialBuilding.objects.filter(project=project, name=name).first()
    )
    was_created = building is None
    if was_created:
        building = IndustrialBuilding(project=project, name=name)
    building.external_number = number
    building.activity = _text(payload.get("type")) or building.activity
    building.declared_units = _int(payload.get("total_units")) or building.declared_units
    building.source_sheet = "Nakhba API"
    if payload:
        building.external_payload = payload
    building.save()
    return building, was_created


def _sync_units(project, rows):
    created = updated = 0
    for position, row in enumerate(rows, start=1):
        building_number = _int(row.get("building_number"))
        unit_number = _text(row.get("unit_number"))
        if not building_number or not unit_number:
            continue
        building, _ = _get_or_update_building(project, building_number)
        area = _decimal(row.get("area"))
        annual_rent = _decimal(row.get("price"))
        rent_per_meter = annual_rent / area if area else Decimal("0")
        status = _status(row.get("status"))
        external_id = _text(row.get("id"))
        record = None
        if external_id:
            record = IndustrialUnitRecord.objects.filter(building=building, external_id=external_id).first()
        if not record:
            record = IndustrialUnitRecord.objects.filter(building=building, unit_number=unit_number).first()
        was_created = record is None
        if was_created:
            record = IndustrialUnitRecord(building=building, unit_number=unit_number)
        record.external_id = external_id
        record.sequence = position
        record.unit_type = _text(row.get("unit_type"))
        record.area = area
        record.activity = _text(row.get("activity"))
        record.rent_per_meter = rent_per_meter
        record.annual_rent = annual_rent
        record.status = status
        record.raw_data = row
        record.save()
        if was_created:
            created += 1
        else:
            updated += 1
    return created, updated


def _sync_tenants(project, rows):
    created = updated = 0
    for row in rows:
        external_id = _text(row.get("id"))
        name = _text(row.get("tenant_name") or row.get("name"))
        phone = _text(row.get("phone"))
        if not name and not external_id:
            continue

        tenant = None
        if external_id:
            tenant = Tenant.objects.filter(project=project, external_id=external_id).first()
        if not tenant and name:
            lookup = Tenant.objects.filter(project=project, name=name)
            tenant = lookup.filter(phone=phone).first() if phone else lookup.first()

        was_created = tenant is None
        if was_created:
            tenant = Tenant(project=project, name=name or external_id)

        tenant.external_id = external_id
        tenant.name = name or tenant.name
        tenant.phone = phone
        tenant.company_name = _text(row.get("business_name"))
        tenant.activity_type = _text(row.get("activity_type"))
        tenant.start_date = _date(row.get("start_date"))
        tenant.notes = _text(row.get("notes"))
        tenant.external_payload = row
        tenant.save()

        _apply_tenant_to_unit(project, tenant, row)

        if was_created:
            created += 1
        else:
            updated += 1
    return created, updated


def _apply_tenant_to_unit(project, tenant, row):
    unit_id = _text(row.get("unit_id"))
    unit = None
    if unit_id:
        unit = IndustrialUnitRecord.objects.filter(building__project=project, external_id=unit_id).select_related("building").first()

    unit_info = row.get("units") or {}
    building_number = _int(unit_info.get("building_number") or row.get("building_number"))
    unit_number = _text(unit_info.get("unit_number") or row.get("unit_number"))
    if not unit and building_number and unit_number:
        unit = IndustrialUnitRecord.objects.filter(
            building__project=project,
            building__external_number=building_number,
            unit_number=unit_number,
        ).select_related("building").first()

    if not unit:
        return

    unit.tenant_name = tenant.name
    unit.phone = tenant.phone
    if tenant.activity_type:
        unit.activity = tenant.activity_type
    unit.contract_start = tenant.start_date
    unit.status = IndustrialUnitRecord.Status.RENTED
    raw_data = unit.raw_data if isinstance(unit.raw_data, dict) else {}
    raw_data["tenant"] = row
    unit.raw_data = raw_data
    unit.save()


def _status(value):
    value = _text(value).lower()
    return {
        "available": IndustrialUnitRecord.Status.VACANT,
        "vacant": IndustrialUnitRecord.Status.VACANT,
        "rented": IndustrialUnitRecord.Status.RENTED,
        "reserved": IndustrialUnitRecord.Status.RESERVED,
    }.get(value, IndustrialUnitRecord.Status.VACANT)


def _text(value):
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _int(value):
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return 0


def _decimal(value):
    if value in (None, ""):
        return Decimal("0")
    try:
        return Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _date(value):
    value = _text(value)
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None
