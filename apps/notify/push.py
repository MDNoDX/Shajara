"""Push notifications to browsers and phones (Web Push, VAPID).

Needs VAPID_PUBLIC_KEY and VAPID_PRIVATE_KEY (see DEPLOY.md). A phone gets
reminders after the site is added to the home screen and notifications are
turned on in Settings → Reminders.
"""
import json
import logging

from django.conf import settings

from .models import PushSubscription

log = logging.getLogger(__name__)


def configured():
    return bool(settings.VAPID_PUBLIC_KEY and settings.VAPID_PRIVATE_KEY)


def send(subscription, payload):
    """Send one message. Returns True if delivered to the push service; a
    subscription the browser has dropped is deleted."""
    from pywebpush import WebPushException, webpush

    try:
        webpush(
            subscription_info={"endpoint": subscription.endpoint,
                               "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth}},
            data=json.dumps(payload, ensure_ascii=False),
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims={"sub": settings.VAPID_SUBJECT},
            ttl=24 * 60 * 60,
            timeout=15,
        )
        return True
    except WebPushException as exc:
        status = getattr(exc.response, "status_code", None)
        if status in (404, 410):
            subscription.delete()
        else:
            log.warning("Web push failed (%s): %s", status, exc)
    except Exception as exc:  # noqa: BLE001 - one bad device must not stop the others
        log.warning("Web push failed: %s", exc)
    return False


def send_to_user(user, payload):
    return sum(send(sub, payload) for sub in PushSubscription.objects.filter(user=user))
