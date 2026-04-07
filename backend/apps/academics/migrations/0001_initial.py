from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="AcademicYear",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("year", models.CharField(max_length=20, unique=True)),
                ("is_active", models.BooleanField(default=False)),
                ("is_archived", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "academics_academic_year",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="academicyear",
            index=models.Index(fields=["is_active"], name="academics_year_active_idx"),
        ),
        migrations.AddIndex(
            model_name="academicyear",
            index=models.Index(fields=["is_archived"], name="academics_year_archived_idx"),
        ),
    ]
