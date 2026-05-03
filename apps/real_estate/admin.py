from django.contrib import admin
from apps.real_estate.models import (
    Collection,
    IndustrialBuilding,
    IndustrialCustomerProfile,
    IndustrialReservationLead,
    IndustrialUnitRecord,
    Installment,
    Lease,
    MaintenanceCost,
    Property,
    RentSchedule,
    Tenant,
    Unit,
)


admin.site.register(Property)
admin.site.register(Unit)
admin.site.register(Tenant)
admin.site.register(Lease)
admin.site.register(RentSchedule)
admin.site.register(Collection)
admin.site.register(Installment)
admin.site.register(MaintenanceCost)


@admin.register(IndustrialBuilding)
class IndustrialBuildingAdmin(admin.ModelAdmin):
    list_display = ("name", "project", "activity", "declared_units", "source_sheet")
    search_fields = ("name", "activity", "project__name")


@admin.register(IndustrialUnitRecord)
class IndustrialUnitRecordAdmin(admin.ModelAdmin):
    list_display = ("unit_number", "building", "status", "tenant_name", "area", "annual_rent", "paid_amount", "remaining_amount")
    list_filter = ("status", "building")
    search_fields = ("unit_number", "tenant_name", "phone", "national_id_or_cr")


@admin.register(IndustrialReservationLead)
class IndustrialReservationLeadAdmin(admin.ModelAdmin):
    list_display = ("customer_name", "phone", "building_name", "unit_number", "status", "request_date")
    search_fields = ("customer_name", "phone", "unit_number")


@admin.register(IndustrialCustomerProfile)
class IndustrialCustomerProfileAdmin(admin.ModelAdmin):
    list_display = ("customer_name", "phone", "activity", "building_name", "relationship_status")
    search_fields = ("customer_name", "phone", "activity", "required_units")
