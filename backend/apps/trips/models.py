from __future__ import annotations

import uuid

from django.db import models


class TripPlan(models.Model):
    """A computed plan, stored so results are shareable and reproducible by URL."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    request = models.JSONField()
    result = models.JSONField()
    heatmap = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"TripPlan {self.id}"
