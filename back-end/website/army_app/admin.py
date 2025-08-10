from django.contrib import admin
from .models import KeyWord, Faction, Stratagem, Detachment, Unit, UnitPointBracket, Enhancement, DataSheet, ArmyList, ArmyListEntry
# Register your models here.

admin.site.register(KeyWord)
admin.site.register(Faction)
admin.site.register(Detachment)
admin.site.register(Stratagem)
admin.site.register(Unit)
admin.site.register(UnitPointBracket)
admin.site.register(Enhancement)
admin.site.register(DataSheet)
admin.site.register(ArmyList)

@admin.register(ArmyListEntry)
class ArmyListEntryAdmin(admin.ModelAdmin):
    list_display = ("army_list", "unit", "model_count", "enhancement", "is_warlord" ,"available_stratagems")

    def available_stratagems(self, obj):
        return ", ".join(strat.name for strat in obj.get_valid_strats())