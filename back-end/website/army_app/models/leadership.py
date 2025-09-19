from django.db import models
from .core import KeyWord
from .units import Unit

class Leadership(models.Model):
    leader = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name="leads")
    attached_unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name="attached_to")
    # Leaders that can share attached units
    co_leaders = models.ManyToManyField("self", 
                                           symmetrical=True, # Captain <--> Lieutenant
                                           blank=True,
                                           help_text="Leaders that can co-lead the same unit.")
    # Restrictions
    required_keywords = models.ManyToManyField(
        KeyWord,
        blank=True,
        related_name="leadership_required_for",
        help_text="Leader must have ALL of these keywords (e.g., RELIC SHIELD)."
    )