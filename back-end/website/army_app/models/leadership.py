from django.db import models
from django.core.exceptions import ValidationError
from .core import KeyWord
from .units import Unit

#TODO decide on wargear_ability restrictions implementation (KeyWord or Ability or new model: Wargear)

class Leadership(models.Model):
    leader = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name="leads")
    attachable_unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name="attached_to")
    # Leaders that can share attached units
    co_leaders = models.ManyToManyField(Unit, blank=True, help_text="Leaders that can co-lead the same unit.")
    # Restrictions - should this be a wargear ability so that it matches Relic Shield in example datasheet?
    keywords = models.ManyToManyField(
        KeyWord,
        blank=True,
        related_name="leadership_required_for",
        help_text="Leader must have ALL of these keywords (e.g., RELIC SHIELD)."
    )

    def __str__(self):
        return f"{self.leader} leads {self.attachable_unit}"
    
    def clean(self):
        super().clean()
        # Validate leader has LEADER keyword
        if not self.leader.keywords.filter(name__iexact="LEADER").exists():
            raise ValidationError(f"{self.leader} does not have LEADER keyword")
        
        # Validate the attachable_unit does not have the LEADER keyword
        if self.attachable_unit.keywords.filter(name__iexact="LEADER").exists():
            raise ValidationError(f"{self.attachable_unit} cannot be attached, it has the LEADER keyword")
        
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Save the object first, then validate co_leaders to prevent m2m error
        invalid_co_leaders = [
            co for co in self.co_leaders.all()
            if not co.keywords.filter(name__iexact="LEADER").exists()
        ]

        if invalid_co_leaders:
            names = ", ".join(str(co) for co in invalid_co_leaders)
            raise ValidationError(f"The following co-leaders do not have the LEADER keyword: {names}")