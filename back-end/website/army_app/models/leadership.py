from django.db import models
from django.core.exceptions import ValidationError
from .core import KeyWord
from .units import Unit

class Leadership(models.Model):
    bodyguard_unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name="lead_by", null=True)
    # Possible leaders
    leader = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name="leads")
    keywords = models.ManyToManyField(
        KeyWord,
        blank=True,
        related_name="leadership_required_for",
        help_text="Leader must have ALL of these keywords (e.g., RELIC SHIELD)."
    )

    def __str__(self):
        return f"{self.leader} leads {self.bodyguard_unit}"
    
    def clean(self):
        super().clean()
        # Validate leader has Leader ability
        if not self.leader.abilities.filter(name__iexact="Leader").exists():
            raise ValidationError(f"{self.leader} does not have Leader ability")
        
        # Validate the bodyguard_unit does not have the Leader ability
        if self.bodyguard_unit.abilities.filter(name__iexact="Leader").exists():
            raise ValidationError(f"{self.bodyguard_unit} cannot be attached, it has the Leader ability")

class Support(models.Model):
    bodyguard_unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name="supported_by")
    support = models.ForeignKey(Unit, on_delete=models.CASCADE, help_text="supports")
    keywords = models.ManyToManyField(
            KeyWord,
            blank=True,
            related_name="support_required_for",
            help_text="Support must have ALL of these keywords (e.g., RELIC SHIELD)."
        )

    def __str__(self):
        return f"{self.support} supports {self.bodyguard_unit}"

    def clean(self):
        super().clean()

        # Validate support has Support ability
        if not self.support.abilities.filter(name__iexact="Support").exists():
            raise ValidationError(f"{self.support} does not have Support ability")

        # Validate the bodyguard_unit does not have the Support ability
        if self.bodyguard_unit.abilities.filter(name__iexact="Support").exists():
            raise ValidationError(f"{self.bodyguard_unit} cannot be attached, it has the Support ability")

