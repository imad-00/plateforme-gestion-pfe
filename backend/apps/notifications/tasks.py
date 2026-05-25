from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from config.celery import app
from apps.notifications.models import Notification, NotificationDelivery


@app.task
def send_notification_email(notification_id):
    notification = Notification.objects.select_related("recipient").filter(pk=notification_id).first()
    if notification is None:
        return
    delivery = NotificationDelivery.objects.filter(
        notification=notification,
        channel=NotificationDelivery.Channel.EMAIL,
    ).first()
    if delivery is None:
        return

    now = timezone.now()
    delivery.attempted_at = now
    recipient_email = (notification.recipient.email or "").strip()
    if not recipient_email:
        delivery.status = NotificationDelivery.Status.SKIPPED
        delivery.error_message = ""
        delivery.save(update_fields=["status", "attempted_at", "error_message", "updated_at"])
        return

    body = notification.message
    if notification.link_url:
        body = f"{body}\n\nLink: {notification.link_url}"

    try:
        send_mail(
            subject=f"[PFE Platform] {notification.title}",
            message=body,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            recipient_list=[recipient_email],
            fail_silently=False,
        )
    except Exception as exc:
        delivery.status = NotificationDelivery.Status.FAILED
        delivery.error_message = str(exc)
        delivery.sent_at = None
        delivery.save(update_fields=["status", "attempted_at", "sent_at", "error_message", "updated_at"])
        return

    delivery.status = NotificationDelivery.Status.SENT
    delivery.sent_at = now
    delivery.error_message = ""
    delivery.save(update_fields=["status", "attempted_at", "sent_at", "error_message", "updated_at"])
