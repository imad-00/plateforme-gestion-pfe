from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("academics", "0001_initial"),
        ("accounts", "0002_studentprofile_teacherprofile"),
    ]

    operations = [
        migrations.AddField(
            model_name="studentprofile",
            name="academic_year",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.SET_NULL,
                related_name="student_profiles",
                to="academics.academicyear",
            ),
        ),
    ]
