from django.db import models
from django.core.exceptions import ValidationError

MAX_CHARFIELD_LENGTH = 255

# Create your models here.

class KeyWord(models.Model):
    name = models.CharField(max_length=MAX_CHARFIELD_LENGTH, unique=True)
    
    # Class functions
    def __str__(self):
        return self.name
    
class Ability(models.Model):
    name = models.CharField(max_length=MAX_CHARFIELD_LENGTH, unique=True)
    description = models.TextField()
    
    class Meta:
        # Change plural in admin so that it doesn't look weird
        verbose_name_plural = "Abilities"

    # Class functions
    def __str__(self):
        return self.name

class Faction(models.Model):
    FACTION_CHOICES = {
        "SPM" : "Space Marines",
        "TYR" : "Tyrannids",
        "ORK" : "Orks",
        "NEC" : "Necrons",
        "CUS" : "Adeptus Custodes"
    }
    name = models.CharField(max_length=MAX_CHARFIELD_LENGTH, choices=FACTION_CHOICES)
    rule_name = models.CharField(max_length=MAX_CHARFIELD_LENGTH)
    rule_description = models.TextField(blank=True, default="")
    keywords = models.ManyToManyField(KeyWord, blank=True)
    
    # Class functions
    def __str__(self):
        return self.name
    
    def clean(self):
        super().clean()
        # Check if name is valid
        valid_choices = ", ".join(key for key in self.FACTION_CHOICES.keys())
        if self.name not in self.FACTION_CHOICES.keys():
            raise ValidationError(f"Invalid Faction: {self.name} does not exist. Valid choices are {valid_choices}")
    
class Detachment(models.Model):
    name = models.CharField(max_length=MAX_CHARFIELD_LENGTH)
    faction = models.ForeignKey(Faction, on_delete=models.CASCADE)
    description = models.TextField(blank=True, default="")
    keywords = models.ManyToManyField(KeyWord, blank=True)
    
    # Class functions
    def __str__(self):
        return self.name

class Enhancement(models.Model):
    name = models.CharField(max_length=MAX_CHARFIELD_LENGTH)
    detachment = models.ForeignKey(Detachment, on_delete=models.CASCADE, related_name="enhancement")
    description = models.TextField(blank=True, default="")
    points = models.PositiveIntegerField()
    keywords = models.ManyToManyField(KeyWord, blank=True)
    
    # Class functions
    def __str__(self):
        return self.name
    
class Stratagem(models.Model):
    name = models.CharField(max_length=MAX_CHARFIELD_LENGTH)
    description = models.TextField(blank=True, default="")
    detachment = models.ForeignKey(Detachment, on_delete=models.CASCADE, null=True, blank=True)
    cost = models.PositiveIntegerField(default=1)
    keywords = models.ManyToManyField(KeyWord, blank=True)
    
    # Class functions
    def __str__(self):
        return self.name
    
    def available_stratagem(self, detachment):
        return self.detachments.filter(pk=detachment.pk).exists()