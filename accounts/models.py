# filepath: accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models


class Role(models.TextChoices):
    REQUESTER = "REQUESTER", "Pemohon"
    APPROVER = "APPROVER", "Approver"
    PROCUREMENT = "PROCUREMENT", "Procurement"
    RECEIVER = "RECEIVER", "Penerima"
    ADMIN = "ADMIN", "Admin"


class User(AbstractUser):
    role = models.CharField("peran", max_length=20, choices=Role.choices, default=Role.REQUESTER)
    version = models.PositiveBigIntegerField(default=1)

    REQUIRED_FIELDS = ["role"]

    class Meta(AbstractUser.Meta):
        constraints = [
            models.CheckConstraint(condition=models.Q(role__in=Role.values), name="user_role_valid"),
            models.CheckConstraint(condition=models.Q(version__gte=1), name="user_version_positive"),
        ]
