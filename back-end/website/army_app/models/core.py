from django.db import models
from django.core.exceptions import ValidationError

MAX_CHARFIELD_LENGTH = 255

# Create your models here.
# TODO: test overriding Enhancement model save function to add CHARACTER keyword automatically

class KeyWord(models.Model):
    name = models.CharField(max_length=MAX_CHARFIELD_LENGTH, unique=True)
    
    # Class functions
    def __str__(self):
        return self.name
    
class Ability(models.Model):
    ABILITY_TYPES = [
        ("FACTION_RULE", "Faction Rule"),
        ("DETACHMENT_RULE", "Detachment Rule"),
        ("UNIT_ABILITY", "Unit Ability"),
        ("WEAPON_ABILITY", "Weapon Ability"),
        ("WARGEAR_ABILITY", "Wargear Ability"),
        ("CORE_RULE", "Core Rule"),
    ]
    
    name = models.CharField(max_length=MAX_CHARFIELD_LENGTH, unique=True)
    description = models.TextField()
    ability_type = models.CharField(max_length=MAX_CHARFIELD_LENGTH, choices=ABILITY_TYPES)
    keywords = models.ManyToManyField(KeyWord, blank=True, related_name="abilities_requiring")
    restricted_keywords = models.ManyToManyField(KeyWord, blank=True, related_name="abilities_forbidding")
    
    class Meta:
        # Change plural in admin so that it doesn't look weird
        verbose_name_plural = "Abilities"

    # Class functions
    def __str__(self):
        return self.get_name_display()

class Faction(models.Model):
    # This gets normalized into list of 2-tuple - [(a, b), (c, d) ...]
    # Perhaps change this to normalized form?
    FACTION_CHOICES = {
        "SPM" : "Space Marines",
        "TYR" : "Tyrannids",
        "ORK" : "Orks",
        "NEC" : "Necrons",
        "CUS" : "Adeptus Custodes",
        "MEC" : "Adeptus Mechanicus",
    }
    name = models.CharField(max_length=MAX_CHARFIELD_LENGTH, choices=FACTION_CHOICES)
    abilities = models.ManyToManyField(Ability, related_name="factions", blank=True, limit_choices_to={"ability_type" : "FACTION_RULE"})
    
    # Class functions
    def __str__(self):
        return self.get_name_display()
    
    def clean(self):
        super().clean()
        # Check if name is valid
        valid_choices = ", ".join(key for key in self.FACTION_CHOICES.keys())
        if self.name not in self.FACTION_CHOICES.keys():
            raise ValidationError(f"Invalid Faction: {self.name} does not exist. Valid choices are {valid_choices}")
    
class Detachment(models.Model):
    name = models.CharField(max_length=MAX_CHARFIELD_LENGTH)
    faction = models.ForeignKey(Faction, on_delete=models.CASCADE)
    abilities = models.ManyToManyField(Ability, related_name="detachments", blank=True, limit_choices_to={"ability_type" : "DETACHMENT_RULE"})
    
    # Class functions
    def __str__(self):
        return self.name

class Enhancement(models.Model):
    name = models.CharField(max_length=MAX_CHARFIELD_LENGTH)
    detachment = models.ForeignKey(Detachment, on_delete=models.CASCADE, related_name="enhancement")
    description = models.TextField(blank=True, default="")
    points = models.PositiveIntegerField()
    keywords = models.ManyToManyField(KeyWord, blank=True, related_name="enhancements_requiring")
    restricted_keywords = models.ManyToManyField(KeyWord, blank=True, related_name="enhancements_forbidding")
    
    # Class functions
    def __str__(self):
        return self.name
    
class Stratagem(models.Model):
    name = models.CharField(max_length=MAX_CHARFIELD_LENGTH)
    description = models.TextField(blank=True, default="")
    detachment = models.ForeignKey(Detachment, on_delete=models.CASCADE, null=True, blank=True)
    cost = models.PositiveIntegerField(default=1)
    keywords = models.ManyToManyField(KeyWord, blank=True, related_name="stratagems_requiring")
    restricted_keywords = models.ManyToManyField(KeyWord, blank=True, related_name="stratagems_forbidding")
    
    # Class functions
    def __str__(self):
        return self.name
    
    def available_stratagem(self, detachment):
        return self.detachments.filter(pk=detachment.pk).exists()