import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class WishList(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        SUBMITTED = "SUBMITTED", "Submitted"
        LOCKED = "LOCKED", "Locked"
        ARCHIVED = "ARCHIVED", "Archived"

    wishlist_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    team = models.ForeignKey(
        "teams.Team",
        on_delete=models.CASCADE,
        related_name="wishlists",
    )
    academic_year = models.ForeignKey(
        "academics.AcademicYear",
        on_delete=models.PROTECT,
        related_name="wishlists",
    )
    selection_round = models.CharField(
        max_length=8,
        choices=[("FIRST", "First"), ("SECOND", "Second")],
        default="FIRST",
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="submitted_wishlists",
        null=True,
        blank=True,
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    locked_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="reviewed_wishlists",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "assignments_wishlist"
        indexes = [
            models.Index(fields=["team"], name="assign_wishlist_team_idx"),
            models.Index(fields=["academic_year"], name="assign_wishlist_year_idx"),
            models.Index(fields=["status"], name="assign_wishlist_status_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["team", "selection_round", "academic_year"],
                name="assign_unique_team_round_wishlist",
            ),
            models.UniqueConstraint(
                fields=["team", "selection_round"],
                name="assign_unique_team_round_wishlist_v2",
            ),
        ]

    def __str__(self):
        return f"{self.team_id} - {self.selection_round} ({self.status})"


class WishItem(models.Model):
    wishitem_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wishlist = models.ForeignKey(
        "assignments.WishList",
        on_delete=models.CASCADE,
        related_name="items",
    )
    subject = models.ForeignKey(
        "topics.Subject",
        on_delete=models.PROTECT,
        related_name="wish_items",
    )
    rank = models.PositiveIntegerField()

    class Meta:
        db_table = "assignments_wish_item"
        constraints = [
            models.UniqueConstraint(fields=["wishlist", "rank"], name="assign_unique_wishitem_rank"),
            models.UniqueConstraint(fields=["wishlist", "subject"], name="assign_unique_subject_once_per_wishlist"),
        ]


class Appeal(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ACCEPTED = "ACCEPTED", "Accepted"
        REJECTED = "REJECTED", "Rejected"

    appeal_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    team = models.OneToOneField(
        "teams.Team",
        on_delete=models.CASCADE,
        related_name="appeal",
    )
    reason = models.TextField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="submitted_appeals",
        null=True,
        blank=True,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reviewed_appeals",
        null=True,
        blank=True,
    )
    submitted_at = models.DateTimeField(default=timezone.now, editable=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    admin_comment = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "assignments_appeal"
        indexes = [
            models.Index(fields=["team"], name="assign_appeal_team_idx"),
            models.Index(fields=["status"], name="assign_appeal_status_idx"),
        ]

    def __str__(self):
        return f"{self.team_id} appeal ({self.status})"
