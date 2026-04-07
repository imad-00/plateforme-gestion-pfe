from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="StudentProfile",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "moyenne_generale",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        max_digits=4,
                        null=True,
                    ),
                ),
                ("specialite", models.CharField(blank=True, max_length=255, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=models.deletion.CASCADE,
                        related_name="student_profile",
                        to="accounts.user",
                    ),
                ),
            ],
            options={
                "db_table": "accounts_student_profile",
            },
        ),
        migrations.CreateModel(
            name="TeacherProfile",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("grade", models.CharField(blank=True, max_length=255, null=True)),
                ("departement", models.CharField(blank=True, max_length=255, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=models.deletion.CASCADE,
                        related_name="teacher_profile",
                        to="accounts.user",
                    ),
                ),
            ],
            options={
                "db_table": "accounts_teacher_profile",
            },
        ),
    ]
