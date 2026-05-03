from django import forms
from apps.real_estate.models import IndustrialCustomerProfile, IndustrialReservationLead, IndustrialUnitRecord


class IndustrialUnitRecordForm(forms.ModelForm):
    class Meta:
        model = IndustrialUnitRecord
        fields = [
            "unit_number",
            "unit_type",
            "area",
            "activity",
            "tenant_name",
            "phone",
            "national_id_or_cr",
            "rent_per_meter",
            "annual_rent",
            "booking_amount",
            "paid_amount",
            "contract_start",
            "contract_end",
            "status",
        ]
        widgets = {
            "contract_start": forms.DateInput(attrs={"type": "date"}),
            "contract_end": forms.DateInput(attrs={"type": "date"}),
        }
        labels = {
            "unit_number": "رقم الوحدة",
            "unit_type": "نوع الوحدة",
            "area": "المساحة",
            "activity": "النشاط",
            "tenant_name": "اسم المستأجر",
            "phone": "رقم التواصل",
            "national_id_or_cr": "الرقم الوطني / السجل التجاري",
            "rent_per_meter": "سعر المتر",
            "annual_rent": "الإيجار السنوي",
            "booking_amount": "مبلغ الحجز",
            "paid_amount": "المدفوع",
            "contract_start": "بداية العقد",
            "contract_end": "نهاية العقد",
            "status": "الحالة",
        }


class IndustrialReservationLeadForm(forms.ModelForm):
    class Meta:
        model = IndustrialReservationLead
        fields = [
            "request_date",
            "customer_name",
            "phone",
            "building_name",
            "unit_number",
            "area",
            "activity",
            "rent_value",
            "booking_amount",
            "status",
            "next_step",
        ]
        widgets = {"request_date": forms.DateInput(attrs={"type": "date"})}
        labels = {
            "request_date": "تاريخ الطلب",
            "customer_name": "اسم العميل",
            "phone": "رقم التواصل",
            "building_name": "المبنى",
            "unit_number": "الوحدة",
            "area": "المساحة",
            "activity": "النشاط",
            "rent_value": "قيمة الإيجار",
            "booking_amount": "مبلغ الحجز",
            "status": "الحالة",
            "next_step": "ملاحظات / الخطوة التالية",
        }


class IndustrialCustomerProfileForm(forms.ModelForm):
    class Meta:
        model = IndustrialCustomerProfile
        fields = [
            "customer_name",
            "contact_person",
            "phone",
            "activity",
            "budget",
            "required_units",
            "building_name",
            "area",
            "source",
            "first_contact",
            "last_contact",
            "relationship_status",
            "next_step",
        ]
        labels = {
            "customer_name": "اسم العميل / المنشأة",
            "contact_person": "جهة الاتصال",
            "phone": "رقم التواصل",
            "activity": "النشاط",
            "budget": "الميزانية",
            "required_units": "الوحدة المطلوبة",
            "building_name": "المبنى",
            "area": "المساحة",
            "source": "مصدر العميل",
            "first_contact": "تاريخ أول تواصل",
            "last_contact": "آخر تواصل",
            "relationship_status": "حالة العلاقة",
            "next_step": "الخطوة التالية",
        }
