from django.apps import AppConfig


class DashboardsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.dashboards"

    def ready(self):
        from django.db.models.signals import post_delete, post_save

        from apps.accounts.models import ProjectMember
        from common.utils import bump_project_version, bump_user_version

        def _project_id_for_instance(instance):
            pid = getattr(instance, "project_id", None)
            if pid:
                return pid

            lease_id = getattr(instance, "lease_id", None)
            if lease_id:
                from apps.real_estate.models import Lease
                return Lease.objects.filter(pk=lease_id).values_list("project_id", flat=True).first()

            property_id = getattr(instance, "property_id", None)
            if property_id:
                from apps.real_estate.models import Property
                return Property.objects.filter(pk=property_id).values_list("project_id", flat=True).first()

            ad_account_id = getattr(instance, "ad_account_id", None)
            if ad_account_id:
                from apps.ads.models import AdAccount
                return AdAccount.objects.filter(pk=ad_account_id).values_list("project_id", flat=True).first()

            return None

        def _bump(project_id):
            if not project_id:
                return
            bump_project_version(project_id)
            user_ids = list(ProjectMember.objects.filter(project_id=project_id, is_active=True).values_list("user_id", flat=True))
            for uid in user_ids:
                bump_user_version(uid)

        def _handler(sender, instance, **kwargs):
            _bump(_project_id_for_instance(instance))

        from apps.finance.models import Transaction
        from apps.ecommerce.models import Order
        from apps.imports.models import UploadedFile, ImportBatch, RawImportedRow
        from apps.integrations.models import RawApiEvent, SyncLog
        from apps.ads.models import AdSpendDaily, AdPerformanceMetric
        from apps.real_estate.models import (
            Property,
            Unit,
            Tenant,
            Lease,
            RentSchedule,
            Collection,
            Installment,
            MaintenanceCost,
        )

        tracked = [
            Transaction,
            Order,
            UploadedFile,
            ImportBatch,
            RawImportedRow,
            RawApiEvent,
            SyncLog,
            AdSpendDaily,
            AdPerformanceMetric,
            Property,
            Unit,
            Tenant,
            Lease,
            RentSchedule,
            Collection,
            Installment,
            MaintenanceCost,
        ]
        for model in tracked:
            post_save.connect(_handler, sender=model, weak=False, dispatch_uid=f"dash_bump_save_{model._meta.label_lower}")
            post_delete.connect(_handler, sender=model, weak=False, dispatch_uid=f"dash_bump_del_{model._meta.label_lower}")
