from datetime import date
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.projects.models import Project, Company
from apps.finance.models import Account, Category, Transaction

class Command(BaseCommand):
    help = "Add expenses for Makkah Industrial City project."

    def handle(self, *args, **options):
        User = get_user_model()
        owner = User.objects.filter(is_superuser=True).first() or User.objects.first()
        
        if not owner:
            self.stdout.write(self.style.ERROR("No user found. Please create a user first."))
            return

        # 1. Get or Create Company
        company, _ = Company.objects.get_or_create(
            name="شركة نخبة تسكين العقارية",
            defaults={
                "owner": owner,
                "country": "SA",
                "base_currency": "SAR",
            }
        )

        # 2. Get or Create Project
        project_name = "المدينة الصناعية بشمال مكة المكرمة"
        project, _ = Project.objects.get_or_create(
            company=company,
            name=project_name,
            defaults={
                "project_type": Project.ProjectType.REAL_ESTATE,
                "country": "SA",
                "base_currency": "SAR",
                "start_date": date(2026, 4, 13),
                "description": "سجل مصاريف مشروع المدينة الصناعية - شمال مكة المكرمة",
            }
        )

        # 3. Get or Create Cash Account
        account, _ = Account.objects.get_or_create(
            project=project,
            name="نقداً",
            defaults={
                "account_type": Account.AccountType.CASH,
                "currency": "SAR",
            }
        )

        # 4. Expenses data
        expenses = [
            {"date": date(2026, 4, 13), "desc": "فيديوهات مونتاج عقاري - فهد المسمار", "amount": 2000, "notes": "تسويق وإعلانات"},
            {"date": date(2026, 4, 13), "desc": "شراء دومين المدينة الصناعية", "amount": 45, "notes": "12 دولار = 45 ريال"},
            {"date": date(2026, 4, 13), "desc": "راتب ندى - سوشيال ميديا (أبريل)", "amount": 500, "notes": "رواتب (شهري)"},
            {"date": date(2026, 4, 13), "desc": "اشتراك فبل (Fabel)", "amount": 469, "notes": "125 دولار = 469 ريال"},
            {"date": date(2026, 4, 13), "desc": "اشتراك السيرفر", "amount": 75, "notes": "20 دولار = 75 ريال"},
            {"date": date(2026, 4, 13), "desc": "اشتراك جوجل بلاي", "amount": 94, "notes": "25 دولار = 94 ريال"},
            {"date": date(2026, 4, 13), "desc": "منصة رسايل تأكيد (5,500 رسالة)", "amount": 650, "notes": "خدمات تقنية"},
            {"date": date(2026, 4, 13), "desc": "اشتراك ChatGPT Team", "amount": 263, "notes": "3,500 جنيه = 263 ريال"},
            {"date": date(2026, 4, 28), "desc": "راتب حسين الشهري (شهر واحد)", "amount": 376, "notes": "5,000 جنيه = 376 ريال"},
            {"date": date(2026, 4, 13), "desc": "إيجار مكتب إداري في مصر (شهر)", "amount": 677, "notes": "9,000 جنيه = 677 ريال"},
        ]

        # 5. Add Transactions
        created_count = 0
        for exp in expenses:
            # Try to find if it already exists to avoid duplicates
            exists = Transaction.objects.filter(
                project=project,
                date=exp["date"],
                amount=exp["amount"],
                description=exp["desc"]
            ).exists()

            if not exists:
                Transaction.objects.create(
                    project=project,
                    account=account,
                    date=exp["date"],
                    amount=exp["amount"],
                    transaction_type=Transaction.TransactionType.EXPENSE,
                    description=exp["desc"],
                    supplier=exp["notes"], # Using supplier or description for notes
                    created_by=owner
                )
                created_count += 1

        self.stdout.write(self.style.SUCCESS(f"Successfully added {created_count} expenses to project '{project.name}'."))
