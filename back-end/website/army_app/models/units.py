from django.db import models
from django.utils.functional import cached_property
from .core import KeyWord, KeyWordCondition, Faction, AbilityEffect
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
    def get_all_keywords(self):
        unit_keywords = self.keywords.all()
        faction_keywords = KeyWord.objects.filter(ability_effect_keywords__ability__granted_to_factions=self.faction).distinct()
        
        return set(unit_keywords) | set(faction_keywords)
    
    
    def eval_unit_condition(self, condition: KeyWordCondition) -> bool:
        all_keywords = self.get_all_keywords()
        # Base Case - check this to make sure it makes sense
        if condition.operator is None:
            return condition.keyword in all_keywords
        
        children = condition.children.all()
        
        # Recursive Case
        if condition.operator == KeyWordCondition.AND:
            return all(self.eval_unit_condition(c) for c in children)
        
        if condition.operator == KeyWordCondition.OR:
            return any(self.eval_unit_condition(c) for c in children)
        
        if condition.operator == KeyWordCondition.NOT:
            return not self.eval_unit_condition(children.first())
    
    def ability_affects_unit(self, ability_effect: AbilityEffect):
        return self.eval_unit_condition(ability_effect.auto_condition)
    
    def applicable_effects(self, detachment=None):
        # Return all ability effects that apply to this unit
        
        # Faction abilities
        effects = AbilityEffect.objects.filter(ability__granted_to_factions=self.faction)
        
        # Include Detachment abilities if given
        if detachment:
            effects = effects.union(AbilityEffect.objects.filter(ability__detachments=detachment))
            
        # Optimize fetching for keywords and KeyWordCondition
        # effects = effects.distinct().select_related("ability").prefetch_related("keywords", "auto_condition__children")
        
        return [
            effect for effect in effects if self.ability_affects_unit(effect)
        ]
    
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