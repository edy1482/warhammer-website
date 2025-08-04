from django.db import models

# Create your models here.
class Faction(models.Model):
    FACTION_CHOICES = {
        "SPM" : "Space Marines",
        "TYR" : "Tyrannids",
        "ORK" : "Orks",
        "NEC" : "Necrons",
    }
    name = models.CharField(max_length=100, choices=FACTION_CHOICES)
    
    # Class functions
    def __str__(self):
        return self.name
    
class Detachment(models.Model):
    name = models.CharField(max_length=200)
    rule = models.TextField()
    

class DataSheet(models.Model):
    name = models.CharField(max_length=200)
    upload_file = models.FileField(upload_to="uploads/%Y/%m/%d/")

class Unit(models.Model):
    faction = models.ForeignKey(Faction, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    num_models = models.PositiveSmallIntegerField()
    points = models.PositiveSmallIntegerField()
    data_sheet = models.ForeignKey(DataSheet, on_delete=models.CASCADE)
    
    # Class functions
    def __str__(self):
        return self.name