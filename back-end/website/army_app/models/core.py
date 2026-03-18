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
    
class KeyWordCondition(models.Model):
    AND = "AND"
    OR = "OR"
    NOT = "NOT"
    
    OPERATOR_CHOICES = [
        (AND, "AND"),
        (OR, "OR"),
        (NOT, "NOT"),
    ]
    
    operator = models.CharField(max_length=MAX_CHARFIELD_LENGTH, choices=OPERATOR_CHOICES, null=True, blank=True, help_text="Logical operator, null means leaf node")
    keyword = models.ForeignKey(KeyWord, null=True, blank=True, on_delete=models.CASCADE, help_text="Set only for leaf nodes")
    
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE, related_name="children")
    
    # Leaf Node:
    # Operator = None
    # Keyword != None
    
    # Operator Node:
    # Operator != None
    # Keyword = None
    
    def clean(self):
        super().clean()
        if self.operator and self.keyword:
            return ValidationError("Operator cannot have keyword")
        
        if self.operator and not self.keyword:
            return ValidationError("Leaf node must have keyword")
        
        if self.operator == self.NOT and self.children.count() != 1:
            return ValidationError("NOT operator must have exactly one child")
    
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
    ability_type = models.CharField(max_length=MAX_CHARFIELD_LENGTH, choices=ABILITY_TYPES)
    
    class Meta:
        # Change plural in admin so that it doesn't look weird
        verbose_name_plural = "Abilities"

    # Class functions
    def __str__(self):
        return self.name
    
class AbilityEffect(models.Model):
    ability = models.ForeignKey(Ability, on_delete=models.CASCADE, related_name="effects")
    # Text for this conditional effect
    effect_description = models.TextField()
       
    # Keywords
    keywords = models.ManyToManyField(KeyWord, related_name="ability_effect_keywords")
    
    # Keyword expression in mini-expression language
    keyword_expression = models.TextField(help_text="e.g. ADEPTUS ASTARTES AND (VEHICLE OR MOUNTED)")
    
    # KeywordCondition - AST to be built after data load
    auto_condition = models.ForeignKey(KeyWordCondition, null=True, blank=True, on_delete=models.SET_NULL)

class Faction(models.Model):
    FACTION_CHOICES = [
        ("SPM", "Space Marines"),
        ("TYR", "Tyrannids"),
        ("ORK", "Orks"),
        ("NEC", "Necrons"),
        ("CUS", "Adeptus Custodes"),
        ("MEC", "Adeptus Mechanicus"),
    ]
    name = models.CharField(max_length=MAX_CHARFIELD_LENGTH, choices=FACTION_CHOICES)
    abilities = models.ManyToManyField(Ability, related_name="granted_to_factions", blank=True, limit_choices_to={"ability_type" : "FACTION_RULE"})
    
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
    
    # Keywords
    keywords = models.ManyToManyField(KeyWord, related_name="ability_keywords")
    
    # Keyword expression in mini-expression language
    keyword_expression = models.TextField(help_text="e.g. ADEPTUS ASTARTES AND (VEHICLE OR MOUNTED)")
    
    # KeywordCondition - AST to be built after data load
    auto_condition = models.ForeignKey(KeyWordCondition, null=True, blank=True, on_delete=models.SET_NULL)
    
    # Class functions
    def __str__(self):
        return self.name
    
class Phase(models.model):
    PHASES = [
        ("COMMAND", "Command phase"),
        ("MOVEMENT", "Movement phase"),
        ("SHOOTING", "Shooting phase"),
        ("CHARGE", "Charge phase"),
        ("Fight", "Fight phase")
    ]
    TURNS = [
        ("YOURS", "Your turn"),
        ("OPP", "Your opponent's turn")
    ]
    name = models.CharField(max_length=MAX_CHARFIELD_LENGTH, choices=PHASES)
    turn = models.CharField(max_length=MAX_CHARFIELD_LENGTH, choices=TURNS)
    
    
class Stratagem(models.Model):
    name = models.CharField(max_length=MAX_CHARFIELD_LENGTH)
    when = models.ManyToManyField(Phase, blank=True, related_name="stratagem_phase")
    target = models.TextField(blank=True, default="")
    effect = models.TextField(blank=True, default="")
    restrictions = models.TextField(blank=True, default="")
    detachment = models.ForeignKey(Detachment, on_delete=models.CASCADE, null=True, blank=True, related_name="stratagems")
    cost = models.PositiveIntegerField(default=1)
    
    # Keywords
    keywords = models.ManyToManyField(KeyWord, related_name="ability_keywords")
    
    # Keyword expression in mini-expression language
    keyword_expression = models.TextField(help_text="e.g. ADEPTUS ASTARTES AND (VEHICLE OR MOUNTED)")
    
    # KeywordCondition - AST to be built after data load
    auto_condition = models.ForeignKey(KeyWordCondition, null=True, blank=True, on_delete=models.SET_NULL)
    
    # Class functions
    def __str__(self):
        return self.name
    
    def available_stratagem(self, detachment):
        return self.detachments.filter(pk=detachment.pk).exists()