from django.db import models
from django.core.exceptions import ValidationError
from .core import KeyWord
from .units import Unit

class Leadership(models.Model):
    leader = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name="leads")
    attached_unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name="attached_to")
    # Leaders that can share attached units
    co_leaders = models.ManyToManyField(Unit, blank=True, help_text="Leaders that can co-lead the same unit.")
    # Restrictions
    keywords = models.ManyToManyField(
        KeyWord,
        blank=True,
        related_name="leadership_required_for",
        help_text="Leader must have ALL of these keywords (e.g., RELIC SHIELD)."
    )

    def __str__(self):
        return f"{self.leader} leads {self.attached_unit}"
    
    def clean(self):
        super().clean()
        for co in self.co_leaders.all():
            reciprocal = Leadership.objects.filter(
                leader=co, attached_unit=self.attached_unit, co_leaders=self.leader
                ).exists()
            if not reciprocal:
                raise ValidationError(
                    f"Missing reciprocal co-leader: {co} must also declare {self.leader} as a co-leader for {self.attached_unit}"
                    )