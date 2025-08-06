from django.db import models
from django.contrib.auth.models import User

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
    }
    name = models.CharField(max_length=MAX_CHARFIELD_LENGTH, choices=FACTION_CHOICES)
    rule_name = models.CharField(max_length=MAX_CHARFIELD_LENGTH)
    faction_rule_description = models.TextField(null=True)
    faction_key_words = models.ManyToManyField(KeyWord, blank=True)
    
    # Class functions
    def __str__(self):
        return self.name
    
class Detachment(models.Model):
    name = models.CharField(max_length=MAX_CHARFIELD_LENGTH)
    faction = models.ForeignKey(Faction, on_delete=models.CASCADE, null=True)
    description = models.TextField(default="")
    key_words = models.ManyToManyField(KeyWord, blank=True)
    
    # Class functions
    def __str__(self):
        return self.name

class Unit(models.Model):
    name = models.CharField(max_length=MAX_CHARFIELD_LENGTH)
    faction = models.ForeignKey(Faction, on_delete=models.CASCADE, null=True)
    key_words = models.ManyToManyField(KeyWord, blank=True)
    
    # Class functions
    def __str__(self):
        return self.name
    
class UnitPointBracket(models.Model):
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name="point_brackets", null=True)
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
    
class DataSheet(models.Model):
    unit = models.OneToOneField(Unit, on_delete=models.CASCADE, related_name="datasheet", null=True)
    upload_file = models.FileField(upload_to=f"datasheets/", null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True, null=True)
    source = models.CharField(max_length=MAX_CHARFIELD_LENGTH, null=True)
    
    # Class functions
    def __str__(self):
        return f"{self.unit.name} : Datasheet"
    
class ArmyList(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=MAX_CHARFIELD_LENGTH)
    faction = models.ForeignKey(Faction, on_delete=models.CASCADE)
    detachment = models.ForeignKey(Detachment, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Class functions
    def __str__(self):
        return self.name
    
class ArmyListEntry(models.Model):
    army_list = models.ForeignKey(ArmyList, on_delete=models.CASCADE, related_name="entries")
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE)
    model_count = models.PositiveIntegerField()
    
    def total_points(self):
        bracket = self.unit.point_brackets.filter(min_models__lte=self.model_count, max_models__gte=self.model_count).first()
        return bracket.points if bracket else 0
    
    # Class functions
    def __str__(self):
        return f"{self.army_list.name} - {self.unit.name}"
    