from django.db import models
from .core import KeyWord, Faction

MAX_CHARFIELD_LENGTH = 255

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
    upload_file = models.FileField(upload_to="datasheets/", blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    source = models.CharField(max_length=MAX_CHARFIELD_LENGTH, default="", blank=True)
    
    # Class functions
    def __str__(self):
        return f"{self.unit.name} : Datasheet"
