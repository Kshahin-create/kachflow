from django.db import models


class Property(models.Model):
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="properties")
    name = models.CharField(max_length=180)
    property_type = models.CharField(max_length=80, blank=True)
    country = models.CharField(max_length=80, blank=True)
    city = models.CharField(max_length=80, blank=True)
    district = models.CharField(max_length=120, blank=True)
    address = models.TextField(blank=True)
    total_area = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    leasable_area = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)


class Unit(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="units")
    unit_number = models.CharField(max_length=80)
    floor = models.CharField(max_length=40, blank=True)
    unit_type = models.CharField(max_length=80, blank=True)
    area = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=40, default="vacant")
    rent_per_meter = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    annual_rent = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)


class Tenant(models.Model):
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="tenants")
    external_id = models.CharField(max_length=100, blank=True, db_index=True)
    name = models.CharField(max_length=180)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    company_name = models.CharField(max_length=180, blank=True)
    activity_type = models.CharField(max_length=180, blank=True)
    start_date = models.DateField(blank=True, null=True)
    national_id_or_cr = models.CharField(max_length=80, blank=True, null=True)
    notes = models.TextField(blank=True)
    external_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    class Meta:
        ordering = ["name", "id"]


class Lease(models.Model):
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="leases")
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="leases")
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name="leases")
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="leases")
    start_date = models.DateField()
    end_date = models.DateField()
    annual_rent = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    payment_frequency = models.CharField(max_length=24, default="annual")
    security_deposit = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(max_length=40, default="active")
    contract_file = models.FileField(upload_to="contracts/", blank=True, null=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)


class RentSchedule(models.Model):
    lease = models.ForeignKey(Lease, on_delete=models.CASCADE, related_name="rent_schedules")
    due_date = models.DateField()
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    remaining_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(max_length=40, default="due")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)


class Collection(models.Model):
    lease = models.ForeignKey(Lease, on_delete=models.CASCADE, related_name="collections")
    rent_schedule = models.ForeignKey(RentSchedule, on_delete=models.SET_NULL, blank=True, null=True, related_name="collections")
    payment_date = models.DateField()
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    account = models.ForeignKey("finance.Account", on_delete=models.SET_NULL, blank=True, null=True)
    payment_method = models.CharField(max_length=80, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)


class Installment(models.Model):
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="installments")
    title = models.CharField(max_length=180)
    due_date = models.DateField()
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    remaining_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(max_length=40, default="due")
    related_object_type = models.CharField(max_length=120, blank=True)
    related_object_id = models.CharField(max_length=80, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)


class MaintenanceCost(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="maintenance_costs")
    unit = models.ForeignKey(Unit, on_delete=models.SET_NULL, blank=True, null=True)
    date = models.DateField()
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    category = models.CharField(max_length=120, blank=True)
    description = models.TextField(blank=True)
    supplier = models.CharField(max_length=180, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)


class IndustrialBuilding(models.Model):
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="industrial_buildings")
    name = models.CharField(max_length=120)
    external_number = models.PositiveIntegerField(blank=True, null=True, db_index=True)
    activity = models.CharField(max_length=180, blank=True)
    declared_units = models.PositiveIntegerField(default=0)
    source_sheet = models.CharField(max_length=180, blank=True)
    external_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("project", "name")
        ordering = ["id"]

    def __str__(self):
        return self.name


class IndustrialUnitRecord(models.Model):
    class Status(models.TextChoices):
        RENTED = "rented", "مؤجر"
        RESERVED = "reserved", "محجوز"
        VACANT = "vacant", "غير مؤجر"

    building = models.ForeignKey(IndustrialBuilding, on_delete=models.CASCADE, related_name="unit_records")
    external_id = models.CharField(max_length=100, blank=True, db_index=True)
    sequence = models.PositiveIntegerField(default=0)
    unit_number = models.CharField(max_length=80)
    unit_type = models.CharField(max_length=80, blank=True)
    area = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    activity = models.CharField(max_length=180, blank=True)
    tenant_name = models.CharField(max_length=220, blank=True)
    phone = models.CharField(max_length=80, blank=True)
    national_id_or_cr = models.CharField(max_length=100, blank=True)
    rent_per_meter = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    annual_rent = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    booking_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    remaining_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    contract_start = models.DateField(blank=True, null=True)
    contract_end = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.VACANT)
    source_row = models.PositiveIntegerField(default=0)
    raw_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("building", "unit_number")
        ordering = ["building_id", "sequence", "unit_number"]

    def save(self, *args, **kwargs):
        if self.area and self.rent_per_meter and not self.annual_rent:
            self.annual_rent = self.area * self.rent_per_meter
        if self.annual_rent is not None:
            self.remaining_amount = max(self.annual_rent - (self.paid_amount or 0), self.annual_rent.__class__("0"))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.building.name} - {self.unit_number}"


class IndustrialReservationLead(models.Model):
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="industrial_reservation_leads")
    request_date = models.DateField(blank=True, null=True)
    customer_name = models.CharField(max_length=220)
    phone = models.CharField(max_length=80, blank=True)
    building_name = models.CharField(max_length=120, blank=True)
    unit_number = models.CharField(max_length=80, blank=True)
    area = models.CharField(max_length=80, blank=True)
    activity = models.CharField(max_length=180, blank=True)
    rent_value = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    booking_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(max_length=80, blank=True)
    next_step = models.TextField(blank=True)
    raw_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.customer_name


class IndustrialCustomerProfile(models.Model):
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="industrial_customer_profiles")
    customer_name = models.CharField(max_length=220)
    contact_person = models.CharField(max_length=180, blank=True)
    phone = models.CharField(max_length=80, blank=True)
    activity = models.CharField(max_length=180, blank=True)
    budget = models.CharField(max_length=120, blank=True)
    required_units = models.CharField(max_length=220, blank=True)
    building_name = models.CharField(max_length=120, blank=True)
    area = models.CharField(max_length=120, blank=True)
    source = models.CharField(max_length=180, blank=True)
    first_contact = models.CharField(max_length=80, blank=True)
    last_contact = models.CharField(max_length=80, blank=True)
    relationship_status = models.CharField(max_length=80, blank=True)
    next_step = models.TextField(blank=True)
    raw_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.customer_name
