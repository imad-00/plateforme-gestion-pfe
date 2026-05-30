from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from config.celery import app


@app.task
def send_phase_closing_soon_reminders():
    """One-shot per-phase reminder fired ~24 h before a phase's end_at.

    Picks phases where:
    - end_at is set and falls within (now, now + 24 h]
    - closing_soon_notified_at is null (not yet sent for this deadline)
    - is_archived is False
    - parent academic year is ACTIVE
    """
    from apps.academics.models import AcademicYear
    from apps.campaigns.models import CampaignPhase
    from apps.notifications.services import NotificationService

    now = timezone.now()
    window_end = now + timedelta(hours=24)
    phases = (
        CampaignPhase.objects.select_related("academic_year")
        .filter(
            is_archived=False,
            end_at__isnull=False,
            end_at__gt=now,
            end_at__lte=window_end,
            closing_soon_notified_at__isnull=True,
            academic_year__status=AcademicYear.Status.ACTIVE,
        )
    )
    for phase in phases:
        with transaction.atomic():
            # Re-fetch under lock to avoid a race with the serializer's
            # closing_soon_notified_at reset path.
            locked = CampaignPhase.objects.select_for_update().get(pk=phase.pk)
            if locked.closing_soon_notified_at is not None:
                continue
            NotificationService.notify_phase_closing_soon(locked)
            locked.closing_soon_notified_at = now
            locked.save(update_fields=["closing_soon_notified_at", "updated_at"])
