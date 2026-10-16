import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies: list[tuple[str, str]] = []

    operations = [
        migrations.CreateModel(
            name="TripPlan",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("request", models.JSONField()),
                ("result", models.JSONField()),
                ("heatmap", models.JSONField(blank=True, null=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
