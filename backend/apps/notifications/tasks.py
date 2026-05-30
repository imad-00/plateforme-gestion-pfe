from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
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

    # Plain-text body — preserved as the fallback (some mail clients only render
    # text/plain, and some spam filters score harshly on multipart with no text
    # alternative).
    plain_body = notification.message
    if notification.link_url:
        plain_body = f"{plain_body}\n\nLink: {notification.link_url}"

    html_body = render_to_string(
        "notifications/emails/notification.html",
        {
            "title": notification.title,
            "message": notification.message,
            "link_url": notification.link_url or "",
            "is_important": notification.importance == Notification.Importance.IMPORTANT,
        },
    )

    try:
        email = EmailMultiAlternatives(
            subject=f"[PFE Platform] {notification.title}",
            body=plain_body,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            to=[recipient_email],
        )
        email.attach_alternative(html_body, "text/html")
        email.send(fail_silently=False)
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
