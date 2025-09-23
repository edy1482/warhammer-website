from django.db import models
from django.core.exceptions import ValidationError

MAX_CHARFIELD_LENGTH = 255
MIN_CHARFIELD_LENGTH = 10

class Ability(models.Model):
    name = models.CharField(max_length=MAX_CHARFIELD_LENGTH, unique=True)
    description = models.TextField()

    def __str__(self):
        return self.name
    
class Weapon(models.Model):
    TYPE_CHOICES = {
        "RANGED" : "Ranged",
        "MELEE" : "Meleee"
    }
    name = models.CharField(max_length=MAX_CHARFIELD_LENGTH)
    type_ = models.CharField(max_length=MIN_CHARFIELD_LENGTH, choices=TYPE_CHOICES)
    range_ = models.CharField(max_length=MIN_CHARFIELD_LENGTH, blank=True, null=True) # e.g. "12\""
    attacks = models.CharField(max_length=MIN_CHARFIELD_LENGTH) # could be 1 or D3
    skill = models.CharField(max_length=MIN_CHARFIELD_LENGTH) # BS or WS
    strength = models.CharField(max_length=MIN_CHARFIELD_LENGTH) # could be 4 or 2D6
    ap = models.CharField(max_length=MIN_CHARFIELD_LENGTH) # could be -1 or -D3
    damage = models.CharField(max_length=MIN_CHARFIELD_LENGTH) # could be 1 or D6
    abilities = models.ManyToManyField(Ability, blank=True) # these are the "keywords" next to weapons e.g. Devastaing Wounds

    def __str__(self):
        return self.name
    
    def clean(self):
        super().clean()
        # Check if type_choice is valid
        valid_choices = ", ".join(key for key in self.TYPE_CHOICES.keys())
        if self.name not in self.TYPE_CHOICES.keys():
            raise ValidationError(f"Invalid weapon type: {self.name} does not exist. Valid choices are {valid_choices}")