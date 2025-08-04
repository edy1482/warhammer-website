from django.db import models
from django.contrib.postgres.fields import ArrayField

# Create your models here.
class Faction(models.Model):
    FACTION_CHOICES = {
        "SPM" : "Space Marines",
        "TYR" : "Tyrannids",
        "ORK" : "Orks",
        "NEC" : "Necrons",
    }
    name = models.CharField(max_length=100, choices=FACTION_CHOICES)
    rule = models.TextField(null=True, blank=True)
    
    # Class functions
    def __str__(self):
        return self.name
    
class Detachment(models.Model):
    name = models.CharField(max_length=200)
    rule = models.TextField(null=True, blank=True)
    
    # Class functions
    def __str__(self):
        return self.name
    

class DataSheet(models.Model):
    name = models.CharField(max_length=200, null=True, blank=True)
    upload_file = models.FileField(upload_to="uploads/%Y/%m/%d/", null=True, blank=True)
    
    # Class functions
    def __str__(self):
        return self.name

class Unit(models.Model):
    faction = models.ForeignKey(Faction, on_delete=models.CASCADE, null=True, blank=True)
    detachment = models.ForeignKey(Detachment, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=200, null=True, blank=True)
    num_models = models.PositiveSmallIntegerField(null=True, blank=True)
    points = models.PositiveSmallIntegerField(null=True, blank=True)
    data_sheet = models.ForeignKey(DataSheet, on_delete=models.CASCADE, null=True, blank=True)
    key_words = ArrayField(models.CharField(max_length=200), null=True, blank=True)
    
    # Class functions
    def __str__(self):
        return self.name