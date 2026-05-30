from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("academics", "0005_academicyear_wishlist_size"),
        ("accounts", "0010_user_must_reset_password"),
    ]

    operations = [
        migrations.AddField(
            model_name="externalsupervisorprofile",
            name="academic_year",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=models.deletion.SET_NULL,
                related_name="external_supervisor_profiles",
                to="academics.academicyear",
            ),
        ),
    ]
