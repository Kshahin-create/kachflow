from datetime import date, timedelta
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from apps.accounts.models import ProjectMember, ProjectStakeholder
from apps.ads.models import AdAccount, AdSpendDaily
from apps.ecommerce.models import Customer, Order, Product
from apps.finance.models import Account, Category, Transaction
from apps.imports.models import ImportTemplate
from apps.investments.models import Asset
from apps.projects.models import Company, Project
from apps.real_estate.models import Lease, Property, Tenant, Unit

User = get_user_model()


class Command(BaseCommand):
    help = "Create demo data for KashFlow MVP."

    def handle(self, *args, **options):
        owner, _ = User.objects.get_or_create(username="owner", defaults={"email": "owner@example.com", "is_staff": True, "is_superuser": True})
        owner.set_password("password123")
        owner.save()
        accountant, _ = User.objects.get_or_create(username="accountant", defaults={"email": "accountant@example.com"})
        partner, _ = User.objects.get_or_create(username="partner", defaults={"email": "partner@example.com"})
        viewer, _ = User.objects.get_or_create(username="viewer", defaults={"email": "viewer@example.com"})
        for user in [accountant, partner, viewer]:
            user.set_password("password123")
            user.save()

        company, _ = Company.objects.get_or_create(name="KashFlow Demo Holding", owner=owner, defaults={"country": "SA", "base_currency": "SAR"})
        specs = [
            ("متجر إلكتروني", "ecommerce"),
            ("مكاتب إدارية", "office"),
            ("مستودعات", "warehouse"),
            ("مشروع إعلانات", "ads"),
            ("محفظة استثمارية", "investment"),
        ]
        projects = []
        for name, kind in specs:
            project, _ = Project.objects.get_or_create(company=company, name=name, defaults={"project_type": kind, "base_currency": "SAR", "country": "SA"})
            projects.append(project)
            ProjectMember.objects.get_or_create(user=owner, project=project, defaults={"role": "owner", "dashboard_access": "full", "can_view_dashboard": True, "can_view_financials": True, "can_manage_users": True, "can_upload_excel": True, "can_import_data": True, "can_view_partner_dashboard": True})
            ProjectMember.objects.get_or_create(user=accountant, project=project, defaults={"role": "accountant", "dashboard_access": "financial", "can_view_dashboard": True, "can_view_financials": True, "can_upload_excel": True, "can_import_data": True})
            ProjectMember.objects.get_or_create(user=viewer, project=project, defaults={"role": "viewer", "dashboard_access": "readonly", "can_view_dashboard": True})

        ecommerce = projects[0]
        ProjectMember.objects.get_or_create(user=partner, project=ecommerce, defaults={"role": "partner", "dashboard_access": "partner", "can_view_dashboard": True, "can_view_partner_dashboard": True, "can_view_profit": True})
        ProjectStakeholder.objects.get_or_create(project=ecommerce, user=partner, defaults={"ownership_percentage": 25, "profit_share_percentage": 25, "capital_contribution": 50000})

        account, _ = Account.objects.get_or_create(project=ecommerce, name="الحساب البنكي الرئيسي", defaults={"account_type": "bank", "current_balance": 125000, "currency": "SAR"})
        income_cat, _ = Category.objects.get_or_create(project=ecommerce, name="مبيعات", defaults={"type": "income"})
        expense_cat, _ = Category.objects.get_or_create(project=ecommerce, name="تشغيل", defaults={"type": "expense"})
        for idx in range(1, 7):
            Transaction.objects.get_or_create(project=ecommerce, account=account, date=date.today() - timedelta(days=idx * 5), transaction_type="income", amount=10000 + idx * 700, currency="SAR", category=income_cat, defaults={"created_by": owner, "description": f"مبيعات شهرية {idx}"})
            Transaction.objects.get_or_create(project=ecommerce, account=account, date=date.today() - timedelta(days=idx * 4), transaction_type="expense", amount=2500 + idx * 180, currency="SAR", category=expense_cat, defaults={"created_by": owner, "description": f"مصروفات تشغيل {idx}"})

        customer, _ = Customer.objects.get_or_create(project=ecommerce, name="عميل تجريبي", defaults={"total_orders": 3, "total_spent": 1500})
        product, _ = Product.objects.get_or_create(project=ecommerce, name="منتج تجريبي", defaults={"sku": "SKU-001", "selling_price": 250, "cost_price": 120})
        Order.objects.get_or_create(project=ecommerce, order_number="ORD-1001", defaults={"customer": customer, "order_date": date.today(), "status": "paid", "gross_total": 500, "net_total": 500})

        real_estate = projects[1]
        prop, _ = Property.objects.get_or_create(project=real_estate, name="برج إداري", defaults={"city": "Riyadh", "total_area": 2000, "leasable_area": 1700})
        unit, _ = Unit.objects.get_or_create(property=prop, unit_number="A-101", defaults={"status": "leased", "annual_rent": 85000})
        tenant, _ = Tenant.objects.get_or_create(project=real_estate, name="شركة مستأجرة")
        Lease.objects.get_or_create(project=real_estate, property=prop, unit=unit, tenant=tenant, defaults={"start_date": date.today(), "end_date": date.today() + timedelta(days=365), "annual_rent": 85000})

        ad_project = projects[3]
        ad_account, _ = AdAccount.objects.get_or_create(project=ad_project, platform="Meta", account_name="Meta Demo")
        AdSpendDaily.objects.get_or_create(project=ad_project, ad_account=ad_account, date=date.today(), defaults={"spend": 1200, "revenue": 5400, "orders": 18})

        Asset.objects.get_or_create(project=projects[4], owner=owner, asset_name="محفظة أسهم", defaults={"asset_type": "stock", "acquisition_cost": 100000, "current_value": 118000})
        ImportTemplate.objects.get_or_create(project=ecommerce, name="قالب معاملات تجريبي", sheet_name="Sheet1", target_type="transactions", created_by=owner)

        self.stdout.write(self.style.SUCCESS("Demo data created. Login with owner/password123."))
