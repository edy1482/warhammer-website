from django.db import models
from django.utils.functional import cached_property
from .core import KeyWord, KeyWordCondition, Faction
from .wargear import Ability, Weapon
import logging

MAX_CHARFIELD_LENGTH = 255
MIN_CHARFIELD_LENGTH = 10
logger = logging.getLogger("datasheet")

class Unit(models.Model):
    name = models.CharField(max_length=MAX_CHARFIELD_LENGTH)
    faction = models.ForeignKey(Faction, on_delete=models.CASCADE)
    keywords = models.ManyToManyField(KeyWord, blank=True)
    
    # core stats
    movement = models.CharField(max_length=MIN_CHARFIELD_LENGTH)
    toughness = models.PositiveIntegerField()
    armour_save = models.CharField(max_length=MIN_CHARFIELD_LENGTH)
    wounds = models.PositiveIntegerField()
    ld = models.CharField(max_length=MIN_CHARFIELD_LENGTH)
    objective_control = models.PositiveIntegerField()
    invulnerable_save = models.CharField(max_length=MIN_CHARFIELD_LENGTH, blank=True, null=True)

    # Abilities (unit-specific)
    abilities = models.ManyToManyField(Ability, blank=True, limit_choices_to={"ability_type" : "UNIT_ABILITY"}, related_name="unit_abilities")

    # Wargear and weapons
    ranged_weapons = models.ManyToManyField(Weapon, blank=True, related_name="datasheets_ranged")
    melee_weapons = models.ManyToManyField(Weapon, blank=True, related_name="datasheets_melee")
    # This dictactes what the models in the unit can take instead of their default loadout
    wargear_options = models.TextField(blank=True, default="")

    # Special wargear abilities (like Relic Shield adds one to the Wounds characteristic)
    wargear_abilities = models.ManyToManyField(Ability, blank=True, limit_choices_to={"ability_type" : "WARGEAR_ABILITY"}, related_name="wargear_abilities")

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Class functions
    def __str__(self):
        return self.name
    
    # Change leader to ability not keyword
    def is_leader(self):
        return self.keywords.filter(name__iexact="LEADER").exists()
    
    # Derived helper properties
    
    @cached_property
    def bracket_data(self):
        # Return a cached list of all point brackets for this datasheet's unit
        output = list(self.point_brackets.all())
        if not output:
            logger.warning(f"No point brackets for {self.unit}")
        return output
    
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
        
    @cached_property
    def all_keywords(self):
        unit_kw = set(self.keywords.values_list("name", flat=True))
        # Faction keywords come from ability effects of faction abilities
        faction_kw = set()
        for ability in self.faction.abilities.all():
            for effect in ability.effects.all():
                faction_kw |= set(effect.and_keywords.values_list("name", flat=True))
                faction_kw |= set(effect.or_keywords.values_list("name", flat=True))
        
        return unit_kw | faction_kw
    
    def eval_condition(self, condition: KeyWordCondition):
        # Base Case
        if condition.operator is None:
            return condition.keyword in self.all_keywords
        
        children = condition.children.all()
        
        # Recursive Case
        if condition.operator == KeyWordCondition.AND:
            return all(self.eval_condition(c) for c in children)
        
        if condition.operator == KeyWordCondition.OR:
            return any(self.eval_condition(c) for c in children)
        
        if condition.operator == KeyWordCondition.NOT:
            return not self.eval_condition(children.first())
    
    def affects_unit(self, ability_effect):
        # Check if this ability effect applies to this unit based on keywords
        unit_keywords = self.all_keywords
        
        # Check AND keywords (must have all)
        and_kw = set(ability_effect.and_keywords.values_list("name", flat=True))
        if not and_kw.issubset(unit_keywords):
            return False
        
        # Check OR keywords if OR keywords exist (need at least one)
        or_kw = set(ability_effect.or_keywords.values_list("name", flat=True))
        if or_kw and not (or_kw & unit_keywords):
            return False
        
        # Check NOT keywords (exclude if any exist)
        not_kw = set(ability_effect.not_keywords.values_list("name", flat=True))
        if not_kw & unit_keywords:
            return False
        
        return True
    
    def applicable_effects(self, detachment=None):
        # Return all ability effects that apply to this unit
        applicable = []
        
        # Faction abilities
        for ability in self.faction.abilities.all():
            for effect in ability.effects.all():
                if self.affects_unit(effect):
                    applicable.append(effect)
        
        # Detachment abilities
        if detachment:
            for ability in detachment.abilities.all():
                for effect in ability.effects.all():
                    if self.affects_unit(effect):
                        applicable.append(effect)
        
        return applicable
    
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