from django.db import models

MAX_CHARFIELD_LENGTH = 255
MIN_CHARFIELD_LENGTH = 10

class Ability(models.Model):
    name = models.CharField(max_length=MAX_CHARFIELD_LENGTH, unique=True)
    description = models.TextField()

    def __str__(self):
        return self.name
    
class Weapon(models.Model):
    type_choices = {
        "RANGED" : "Ranged",
        "MELEE" : "Meleee"
    }
    name = models.CharField(max_length=MAX_CHARFIELD_LENGTH)
    type_ = models.CharField(max_length=MIN_CHARFIELD_LENGTH, choices=type_choices)
    range_ = models.CharField(max_length=MIN_CHARFIELD_LENGTH, blank=True, null=True) # e.g. "12\""
    attacks = models.CharField(max_length=MIN_CHARFIELD_LENGTH) # could be 1 or D3
    skill = models.CharField(max_length=MIN_CHARFIELD_LENGTH) # BS or WS
    strength = models.CharField(max_length=MIN_CHARFIELD_LENGTH) # could be 4 or 2D6
    ap = models.CharField(max_length=MIN_CHARFIELD_LENGTH) # could be -1 or -D3
    damage = models.CharField(max_length=MIN_CHARFIELD_LENGTH) # could be 1 or D6
    abilitites = models.ManyToManyField(Ability, blank=True) # these are the "keywords" next to weapons e.g. Devastaing Wounds

    def __str__(self):
        return self.name