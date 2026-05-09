from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ecommerce", "0002_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="customer",
            name="external_id",
            field=models.CharField(blank=True, db_index=True, max_length=160),
        ),
        migrations.AddField(
            model_name="customer",
            name="raw_data",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="order",
            name="external_id",
            field=models.CharField(blank=True, db_index=True, max_length=160),
        ),
        migrations.AddField(
            model_name="order",
            name="raw_data",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="product",
            name="external_id",
            field=models.CharField(blank=True, db_index=True, max_length=160),
        ),
        migrations.AddField(
            model_name="product",
            name="handle",
            field=models.CharField(blank=True, max_length=180),
        ),
        migrations.AddField(
            model_name="product",
            name="raw_data",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
