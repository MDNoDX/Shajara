from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _


class FriendRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", _("Waiting for an answer")
        ACCEPTED = "accepted", _("Accepted")
        DECLINED = "declined", _("Declined")

    from_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="friend_requests_sent")
    to_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="friend_requests_received")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _("friend request")
        verbose_name_plural = _("friend requests")
        constraints = [
            models.UniqueConstraint(fields=["from_user", "to_user"], name="unique_friend_request"),
            models.CheckConstraint(condition=~Q(from_user=models.F("to_user")), name="no_self_friend_request"),
        ]
        ordering = ["-created_at"]
