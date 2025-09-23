from django.db import models
from django.utils.functional import cached_property
from .core import KeyWord, Faction
from .wargear import Ability, Weapon
import logging

MAX_CHARFIELD_LENGTH = 255
MIN_CHARFIELD_LENGTH = 10
logger = logging.getLogger("datasheet")

class Unit(models.Model):
    name = models.CharField(max_length=MAX_CHARFIELD_LENGTH)
    faction = models.ForeignKey(Faction, on_delete=models.CASCADE)
    keywords = models.ManyToManyField(KeyWord, blank=True)

    # Class functions
    def __str__(self):
        return self.name
    
    def is_leader(self):
        return self.keywords.filter(name__iexact="LEADER").exists()
    
class UnitPointBracket(models.Model):
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name="point_brackets")
    min_models = models.PositiveIntegerField(default=1)
    max_models = models.PositiveIntegerField(default=1)
    points = models.PositiveIntegerField()
    
    class Meta:
        ordering = ["min_models"]
    
    # Class functions
    def __str__(self):
        return f"{self.unit.name} : {self.min_models} - {self.max_models} = {self.points}"
    
    def contains(self, model_count):
        return self.min_models <= model_count <= self.max_models
    
class DataSheet(models.Model):
    unit = models.OneToOneField(Unit, on_delete=models.CASCADE, related_name="datasheet")

    # core stats
    movement = models.CharField(max_length=MIN_CHARFIELD_LENGTH)
    toughness = models.PositiveIntegerField()
    save = models.CharField(max_length=MIN_CHARFIELD_LENGTH)
    wounds = models.PositiveIntegerField()
    leadership = models.CharField(max_length=MIN_CHARFIELD_LENGTH)
    objective_control = models.PositiveIntegerField()
    invulnerable_save = models.CharField(max_length=MIN_CHARFIELD_LENGTH, blank=True, null=True)

    # Abilities (unit-specific)
    abilities = models.ManyToManyField(Ability, blank=True, related_name="datasheet_abilities")

    # Wargear and weapons
    ranged_weapons = models.ManyToManyField(Weapon, blank=True, related_name="datasheets_ranged")
    melee_weapons = models.ManyToManyField(Weapon, blank=True, related_name="datasheets_melee")
    # This dictactes what the models in the unit can take instead of their default loadout
    wargear_options = models.TextField(blank=True, default="")

    # Special wargear abilities (like Relic Shield adds one to the Wounds characteristic)
    wargear_abilities = models.ManyToManyField(Ability, blank=True, related_name="datasheet_wargear")

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Derived helpers

    @cached_property
    def bracket_data(self):
        # Return a cached list of all point brackets for this datasheet's unit
        output = list(self.unit.point_brackets.all())
        if not output:
            logger.warning(f"No point brackets for {self.unit}")
        return output

    @property
    def faction_rule(self):
        return {
            "name" : self.unit.faction.rule_name,
            "description" : self.unit.faction.rule_description
        }
    
    # --- String representation (for admin/display) ---
    @property
    def composition_and_points_display(self):
        brackets = self.bracket_data
        
        parts = []
        for b in brackets:
            if b.min_models == b.max_models == 1:
                # Single-mode leader style
                parts.append(f"1 {self.unit.name} ({b.points}) pts")
            elif b.min_models == b.max_models:
                # Fixed squad size
                parts.append(f"{b.min_models} {self.unit.name}s ({b.points}) pts")
            else:
                # Variable squad size
                parts.append(f"{b.min_models} - {b.max_models} {self.unit.name}s ({b.points}) pts")
        
        return "; ".join(parts)
        
    # --- Structured representation (for APIs/views) ---
    @property
    def composition_and_points(self):
        return [
            {
                "min_models" : b.min_models,
                "max_models" : b.max_models,
                "points" : b.points,
            }
            for b in self.bracket_data
        ]

    # Class functions
    def __str__(self):
        return f"{self.unit.name} : Datasheet"