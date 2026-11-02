from django.db import models
from django.core.exceptions import ValidationError
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

    class Meta:
        constraints = [models.UniqueConstraint(fields=["faction", "name"], name="unique_unit_per_faction")]

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
            logger.warning(f"No point brackets for {self}")
        return output

    @property
    def has_tiered_points(self):
        # True if the price changes depending on how many copies of this unit are taken
        return any(b.is_tiered for b in self.bracket_data)

    def brackets_for_unit_number(self, unit_number):
        # Brackets that apply to the nth copy of this unit in an army list
        return [b for b in self.bracket_data if b.applies_to_unit_number(unit_number)]

    def points_for(self, model_count, unit_number=1):
        # Points for the nth copy of this unit at a given model count (0 if no bracket matches)
        for b in self.brackets_for_unit_number(unit_number):
            if b.contains(model_count):
                return b.points
        return 0

    # --- String representation (for admin/display) ---
    @property
    def composition_and_points_display(self):
        brackets = self.bracket_data
        tiered = self.has_tiered_points

        parts = []
        for b in brackets:
            if b.min_models == b.max_models == 1:
                # Single-mode leader style
                text = f"1 {self.name} ({b.points}) pts"
            elif b.min_models == b.max_models:
                # Fixed squad size
                text = f"{b.min_models} {self.name}s ({b.points}) pts"
            else:
                # Variable squad size
                text = f"{b.min_models} - {b.max_models} {self.name}s ({b.points}) pts"
            if tiered:
                text = f"{b.unit_number_display} unit: {text}"
            parts.append(text)

        return "; ".join(parts)

    # --- Structured representation (for APIs/views) ---
    @property
    def composition_and_points(self):
        return [
            {
                "min_models" : b.min_models,
                "max_models" : b.max_models,
                "min_unit_number" : b.min_unit_number,
                "max_unit_number" : b.max_unit_number,
                "points" : b.points,
            }
            for b in self.bracket_data
        ]
        
    @cached_property
    def get_all_keywords(self):
        unit_keywords = self.keywords.all()
        faction_keywords = KeyWord.objects.filter(ability_effect_keywords__ability__granted_to_factions=self.faction).distinct()
        
        return set(unit_keywords) | set(faction_keywords)
    
    
    def ability_affects_unit(self, ability_effect: AbilityEffect):
        return ability_effect.auto_condition.eval_unit_condition(self)
    
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
    """
    Points for a unit at a given model count, optionally depending on how many
    copies of that unit are already in the army list.

    e.g. "Your 1st to 3rd units cost 240, your 4th+ unit costs 270":
        min_unit_number=1, max_unit_number=3,    points=240
        min_unit_number=4, max_unit_number=None, points=270

    Units with a single price keep the defaults (1 to None = every copy).
    """
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name="point_brackets")
    min_models = models.PositiveIntegerField(default=1)
    max_models = models.PositiveIntegerField(default=1)
    # Which copies of this unit in an army list this price applies to (1 = the first one taken)
    min_unit_number = models.PositiveIntegerField(default=1, help_text="First copy of the unit this price applies to (1 = 1st unit)")
    max_unit_number = models.PositiveIntegerField(null=True, blank=True, help_text="Last copy this price applies to. Leave blank for no limit (e.g. 4th+)")
    points = models.PositiveIntegerField()

    class Meta:
        ordering = ["min_unit_number", "min_models"]
        constraints = [
            models.UniqueConstraint(
                fields=["unit", "min_models", "max_models", "min_unit_number"],
                name="unique_bracket_per_unit",
            ),
        ]

    # Class functions
    def __str__(self):
        base = f"{self.unit.name} : {self.min_models} - {self.max_models} = {self.points}"
        if self.is_tiered:
            return f"{base} ({self.unit_number_display} unit)"
        return base

    def clean(self):
        super().clean()
        errors = {}
        if self.min_models is not None and self.max_models is not None and self.min_models > self.max_models:
            errors["max_models"] = "max_models must be greater than or equal to min_models"
        if self.min_unit_number is not None and self.min_unit_number < 1:
            errors["min_unit_number"] = "min_unit_number must be at least 1"
        if self.max_unit_number is not None and self.min_unit_number is not None and self.max_unit_number < self.min_unit_number:
            errors["max_unit_number"] = "max_unit_number must be blank or greater than or equal to min_unit_number"
        if errors:
            raise ValidationError(errors)

        # Two brackets must never both price the same copy at the same model count,
        # e.g. an old "every copy = 240" row left in place next to a new "4th+ = 270" row
        overlapping = self.overlapping_brackets()
        if overlapping:
            clashes = ", ".join(str(b) for b in overlapping)
            raise ValidationError(f"Overlapping point brackets for {self.unit.name}: {self} overlaps {clashes}")

    def overlapping_brackets(self):
        if not self.unit_id or None in (self.min_models, self.max_models, self.min_unit_number):
            return []
        siblings = (
            UnitPointBracket.objects
            .filter(unit_id=self.unit_id, min_models__lte=self.max_models, max_models__gte=self.min_models)
            # Same natural key = the row the CSV loader is about to update, not a clash
            .exclude(min_models=self.min_models, max_models=self.max_models, min_unit_number=self.min_unit_number)
        )
        if self.pk:
            siblings = siblings.exclude(pk=self.pk)
        if self.max_unit_number is not None:
            siblings = siblings.filter(min_unit_number__lte=self.max_unit_number)
        siblings = siblings.filter(models.Q(max_unit_number__isnull=True) | models.Q(max_unit_number__gte=self.min_unit_number))
        return list(siblings)

    @property
    def is_tiered(self):
        # True when this price only applies to some copies of the unit
        return not (self.min_unit_number == 1 and self.max_unit_number is None)

    @property
    def unit_number_display(self):
        # "1st-3rd", "4th+", "1st"
        if self.max_unit_number is None:
            return f"{ordinal(self.min_unit_number)}+"
        if self.min_unit_number == self.max_unit_number:
            return ordinal(self.min_unit_number)
        return f"{ordinal(self.min_unit_number)}-{ordinal(self.max_unit_number)}"

    def contains(self, model_count):
        return self.min_models <= model_count <= self.max_models

    def applies_to_unit_number(self, unit_number):
        if unit_number < self.min_unit_number:
            return False
        return self.max_unit_number is None or unit_number <= self.max_unit_number

    @classmethod
    def for_unit_number_q(cls, unit_number):
        # Q filter selecting brackets that apply to the nth copy of a unit
        return models.Q(min_unit_number__lte=unit_number) & (
            models.Q(max_unit_number__isnull=True) | models.Q(max_unit_number__gte=unit_number)
        )


def ordinal(n):
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"