from django.db import models
from django.db.models import Count
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

MAX_CHARFIELD_LENGTH = 255

# Create your models here.

class KeyWord(models.Model):
    name = models.CharField(max_length=MAX_CHARFIELD_LENGTH, unique=True)
    
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
        

class Unit(models.Model):
    name = models.CharField(max_length=MAX_CHARFIELD_LENGTH)
    faction = models.ForeignKey(Faction, on_delete=models.CASCADE)
    keywords = models.ManyToManyField(KeyWord, blank=True)
    
    # Class functions
    def __str__(self):
        return self.name
    
class UnitPointBracket(models.Model):
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name="point_brackets")
    min_models = models.PositiveIntegerField(default=1)
    max_models = models.PositiveIntegerField(default=1)
    points = models.PositiveIntegerField()
    
    # Class functions
    class Meta:
        ordering = ["min_models"]
    
    def __str__(self):
        return f"{self.unit.name} : {self.min_models} - {self.max_models} = {self.points}"
    
    def contains(self, model_count):
        return self.min_models <= model_count <= self.max_models
    
class Enhancement(models.Model):
    name = models.CharField(max_length=MAX_CHARFIELD_LENGTH)
    detachment = models.ForeignKey(Detachment, on_delete=models.CASCADE, related_name="enhancement")
    description = models.TextField(blank=True, default="")
    points = models.PositiveIntegerField()
    keywords = models.ManyToManyField(KeyWord, blank=True)
    
    # Class functions
    def __str__(self):
        return self.name
    
class DataSheet(models.Model):
    unit = models.OneToOneField(Unit, on_delete=models.CASCADE, related_name="datasheet")
    upload_file = models.FileField(upload_to=f"datasheets/", blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    source = models.CharField(max_length=MAX_CHARFIELD_LENGTH, default="", blank=True)
    
    # Class functions
    def __str__(self):
        return f"{self.unit.name} : Datasheet"
    
class ArmyList(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=MAX_CHARFIELD_LENGTH, blank=True, default="")
    faction = models.ForeignKey(Faction, on_delete=models.CASCADE)
    detachment = models.ForeignKey(Detachment, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Class functions
    def __str__(self):
        return self.name
    
class ArmyListEntry(models.Model):
    army_list = models.ForeignKey(ArmyList, on_delete=models.CASCADE, related_name="entries")
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE)
    model_count = models.PositiveIntegerField(default=1)
    enhancement = models.ForeignKey(Enhancement, on_delete=models.SET_NULL, blank=True, null=True)
    is_warlord = models.BooleanField(default=False)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["army_list", "enhancement"], 
                name="unique_enhancement_per_army_list", 
                condition = models.Q(enhancement__isnull=False)),
            ]
    
    # Class functions
    def __str__(self):
        return f"{self.army_list.name} - {self.unit.name}"
    
    def get_unit_points(self):
        bracket = self.unit.point_brackets.filter(min_models__lte=self.model_count, max_models__gte=self.model_count).first()
        return bracket.points if bracket else 0
    
    def get_enhancement_points(self):
        return self.enhancement.points if self.enhancement else 0
    
    def get_total_points(self):
        return self.get_unit_points() + self.get_enhancement_points()
    
    def get_valid_strats(self):
        # Grab all CORE strats
        core_strats = Stratagem.objects.filter(keywords__name="CORE")
        # Grab all detachment strats, and filter for necessary keywords
        detachment_strats = Stratagem.objects.filter(detachment=self.army_list.detachment).filter(keywords__in=self.unit.keywords.all())

        return (core_strats | detachment_strats).distinct()
        
    
    def clean(self):
        super().clean()
        # Check if Entry is a Warlord
        if self.is_warlord:
            # Must have character key word
            if not self.unit.keywords.filter(name__iexact="CHARACTER").exists():
                raise ValidationError(f"Missing Keyword: {self.unit.name} is not a CHARACTER")
            
            # There must not be an existing Warlord
            
            other_warlords = ArmyListEntry.objects.filter(army_list=self.army_list, is_warlord=True).exclude(pk=self.pk)
            if other_warlords.exists():
                # Do a join on the whole object in case there are multiple duplicates - this should not happen but it is good to check 
                warlord_names = ", ".join(warlord.unit.name for warlord in other_warlords)
                raise ValidationError(f"Duplicate Warlord: {self.unit.name} cannot be the Warlord - there is already an existing Warlord: {warlord_names}")
        
        # Check if there is an enhancement and a unit
        if self.enhancement and self.unit:
            # Do a check to see if the enhancement already exists
            duplicate_enhancement = ArmyListEntry.objects.filter(army_list=self.army_list, enhancement=self.enhancement).exclude(pk=self.pk)
            if duplicate_enhancement.exists():
                # Do a join on the whole object in case there are multiple duplicates - this should not happen but it is good to check 
                unit_names = ", ".join(dup.unit.name for dup in duplicate_enhancement)
                raise ValidationError(f"Duplicate Enhancement: the enhancement {self.enhancement.name} is already assigned to another unit: {unit_names} in this list")
            # Do a check to see if the keywords match 
            enhancement_keywords = set(self.enhancement.keywords.all().values_list("name", flat=True))
            unit_keywords = set(self.unit.keywords.all().values_list("name", flat=True))
            if not enhancement_keywords.issubset(unit_keywords):
                difference = enhancement_keywords.difference(unit_keywords)
                missing_keywords = ", ".join(name for name in difference)
                raise ValidationError(f"Missing Keyword(s): {missing_keywords}")
        

    def save(self, *args, **kwargs):
        # Ensure clean() is called when saving from shell or script
        self.full_clean()
        # Save to ensure id field
        super().save(*args, **kwargs)
        
        # WARLORD keyword insertion/deletion
        warlord_keyword, _ = KeyWord.objects.get_or_create(name = "WARLORD")
        if self.is_warlord:
            # Add WARLORD keyword
            if not self.unit.keywords.filter(pk=warlord_keyword.pk).exists():
                self.unit.keywords.add(warlord_keyword)
        else:
            # Remove WARLORD keyword
            if self.unit.keywords.filter(pk=warlord_keyword.pk).exists():
                self.unit.keywords.remove(warlord_keyword)
                
    def delete(self, *args, **kwargs):
        warlord_key_word = KeyWord.objects.filter(name__iexact="WARLORD").first()
        if self.is_warlord and warlord_key_word:
            if self.unit.keywords.filter(pk=warlord_key_word.pk).exists():
                self.unit.keywords.remove(warlord_key_word)
        
        return super().delete(*args, **kwargs)
    