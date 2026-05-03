from django.core.management.base import BaseCommand, CommandError

from apps.integrations.models import ApiConnection
from apps.integrations.nakhba import DEFAULT_BASE_URL, NAKHBA_PROVIDER, sync_nakhba_connection
from apps.projects.models import Project


class Command(BaseCommand):
    help = "Sync Nakhba Taskin REST API into the selected industrial city project."

    def add_arguments(self, parser):
        parser.add_argument("--project-id", type=int, default=None)
        parser.add_argument("--api-key", default="")
        parser.add_argument("--base-url", default=DEFAULT_BASE_URL)

    def handle(self, *args, **options):
        project = Project.objects.filter(pk=options["project_id"]).first() if options["project_id"] else Project.objects.first()
        if not project:
            raise CommandError("No project found.")
        connection, _ = ApiConnection.objects.get_or_create(
            project=project,
            provider=NAKHBA_PROVIDER,
            defaults={"name": "نخبة تسكين API", "credentials": {"base_url": options["base_url"]}},
        )
        credentials = connection.credentials or {}
        credentials["base_url"] = options["base_url"] or DEFAULT_BASE_URL
        if options["api_key"]:
            credentials["api_key"] = options["api_key"]
        connection.credentials = credentials
        connection.status = "configured"
        connection.save(update_fields=["credentials", "status"])
        sync_log = sync_nakhba_connection(connection)
        self.stdout.write(self.style.SUCCESS(
            f"Synced {sync_log.records_fetched} records. Created {sync_log.records_created}, updated {sync_log.records_updated}."
        ))
