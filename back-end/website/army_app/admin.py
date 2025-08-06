from django.contrib import admin
from .models import KeyWord, Faction, Detachment, Unit, UnitPointBracket, DataSheet, ArmyList, ArmyListEntry
# Register your models here.

admin.site.register(KeyWord)
admin.site.register(Faction)
admin.site.register(Detachment)
admin.site.register(Unit)
admin.site.register(UnitPointBracket)
admin.site.register(DataSheet)
admin.site.register(ArmyList)
admin.site.register(ArmyListEntry)