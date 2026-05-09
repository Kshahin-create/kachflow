import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import ProjectMember
from apps.integrations.models import ApiConnection
from apps.projects.models import Company, Project


WUILT_PROVIDER = "wuilt"
WUILT_GRAPHQL_ENDPOINT = "https://graphql.wuilt.com/"
DEFAULT_PROJECT_NAME = "Bahiah-باهيَةْ"


class Command(BaseCommand):
    help = "Create or update the Bahiah ecommerce project and its Wuilt API connection."

    def add_arguments(self, parser):
        parser.add_argument("--owner", default="owner", help="Username that owns the project membership.")
        parser.add_argument("--company", default="KashFlow Demo Holding", help="Company name to attach the project to.")
        parser.add_argument("--project-name", default=DEFAULT_PROJECT_NAME)
        parser.add_argument("--api-key", default=os.environ.get("WUILT_API_KEY", ""), help="Wuilt API key.")
        parser.add_argument("--store-id", default=os.environ.get("WUILT_STORE_ID", ""), help="Optional Wuilt store id.")

    def handle(self, *args, **options):
        api_key = (options["api_key"] or "").strip()
        if not api_key:
            raise CommandError("Pass --api-key or set WUILT_API_KEY.")

        User = get_user_model()
        owner = User.objects.filter(username=options["owner"]).first()
        if not owner:
            owner = User.objects.filter(is_superuser=True).order_by("id").first()
        if not owner:
            raise CommandError("No owner user was found. Create a user first.")

        company, _ = Company.objects.get_or_create(
            name=options["company"],
            defaults={"owner": owner, "country": "EG", "base_currency": "EGP"},
        )
        if company.owner_id != owner.id and not company.owner_id:
            company.owner = owner
            company.save(update_fields=["owner"])

        project, project_created = Project.objects.get_or_create(
            company=company,
            name=options["project_name"],
            defaults={
                "project_type": Project.ProjectType.ECOMMERCE,
                "country": "EG",
                "base_currency": "EGP",
                "description": "Bahiah store connected to Wuilt GraphQL API.",
            },
        )
        updates = []
        if project.project_type != Project.ProjectType.ECOMMERCE:
            project.project_type = Project.ProjectType.ECOMMERCE
            updates.append("project_type")
        if project.base_currency != "EGP":
            project.base_currency = "EGP"
            updates.append("base_currency")
        if project.country != "EG":
            project.country = "EG"
            updates.append("country")
        if updates:
            project.save(update_fields=updates)

        ProjectMember.objects.get_or_create(
            user=owner,
            project=project,
            defaults={
                "role": ProjectMember.Role.OWNER,
                "dashboard_access": ProjectMember.DashboardAccess.FULL,
                "can_view_dashboard": True,
                "can_view_financials": True,
                "can_manage_users": True,
                "can_upload_excel": True,
                "can_import_data": True,
                "can_view_customers": True,
                "can_view_profit": True,
                "can_export_reports": True,
            },
        )

        credentials = {
            "endpoint": WUILT_GRAPHQL_ENDPOINT,
            "api_key": api_key,
        }
        store_id = (options["store_id"] or "").strip()
        if store_id:
            credentials["store_id"] = store_id

        connection, connection_created = ApiConnection.objects.update_or_create(
            project=project,
            provider=WUILT_PROVIDER,
            defaults={
                "name": "Wuilt GraphQL API",
                "credentials": credentials,
                "status": "configured" if store_id else "missing_store_id",
                "created_by": owner,
            },
        )

        state = "created" if project_created else "updated"
        connection_state = "created" if connection_created else "updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"Bahiah project {state}; Wuilt connection {connection_state}; "
                f"project_id={project.id}; connection_id={connection.id}; status={connection.status}."
            )
        )
