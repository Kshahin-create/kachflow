from django.core.management.base import BaseCommand, CommandError

from apps.integrations.models import ApiConnection
from apps.integrations.wuilt import WUILT_PROVIDER, sync_wuilt_connection


class Command(BaseCommand):
    help = "Sync ecommerce data from a Wuilt API connection."

    def add_arguments(self, parser):
        parser.add_argument("--project-id", type=int, help="Project id to sync.")
        parser.add_argument("--connection-id", type=int, help="Specific ApiConnection id to sync.")

    def handle(self, *args, **options):
        qs = ApiConnection.objects.filter(provider=WUILT_PROVIDER).select_related("project")
        if options.get("connection_id"):
            qs = qs.filter(id=options["connection_id"])
        if options.get("project_id"):
            qs = qs.filter(project_id=options["project_id"])
        connection = qs.order_by("-created_at").first()
        if not connection:
            raise CommandError("No Wuilt API connection found.")
        log = sync_wuilt_connection(connection)
        self.stdout.write(
            self.style.SUCCESS(
                f"Synced {connection.project.name}: fetched={log.records_fetched}, "
                f"created={log.records_created}, updated={log.records_updated}."
            )
        )
