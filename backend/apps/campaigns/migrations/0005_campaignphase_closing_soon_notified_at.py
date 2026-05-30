from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('campaigns', '0004_alter_campaignphase_phase_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='campaignphase',
            name='closing_soon_notified_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
