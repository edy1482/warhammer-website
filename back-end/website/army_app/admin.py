from django.contrib import admin
from .models import KeyWord, Faction, Detachment, Stratagem, Unit, UnitPointBracket, Enhancement, DataSheet, ArmyList, ArmyListEntry
# Register your models here.

@admin.register(KeyWord)
class KeyWordAdmin(admin.ModelAdmin):
    search_fields = ("name",)
    
@admin.register(Faction)
class FactionAdmin(admin.ModelAdmin):
    search_fields = ("name",)

@admin.register(Detachment)
class DetachmentAdmin(admin.ModelAdmin):
    list_display = ("name", "faction")
    search_fields = ("name",)
    list_filter = ("faction",)

@admin.register(Stratagem)
class StratagemAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    list_filter = ("detachment",)

@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ("name", "faction")
    search_fields = ("name",)
    list_filter = ("faction", "keywords",)
    filter_horizontal = ("keywords",)
    ordering = ("name",)

@admin.register(UnitPointBracket)
class UnitPointBracketAdmin(admin.ModelAdmin):
    list_display = ("unit", "points")
    search_fields = ("unit__name",) # Search fields expect columns, so double underscore
    list_filter = ("unit__faction",)
    
@admin.register(Enhancement)
class EnhancementAdmin(admin.ModelAdmin):
    list_display = ("name", "detachment", "points",)
    search_fields = ("name",)
    list_filter = ("detachment__faction",)

@admin.register(DataSheet)
class DataSheetAdmin(admin.ModelAdmin):
    list_display = ("unit", "upload_file", "source")
    search_fields = ("unit__name",)
    list_filter = ("unit__faction",)

@admin.register(ArmyList)
class ArmyListAdmin(admin.ModelAdmin):
    list_display = ("user", "name", "faction", "detachment")
    search_fields = ("name",)
    list_filter = ("faction", "detachment")

@admin.register(ArmyListEntry)
class ArmyListEntryAdmin(admin.ModelAdmin):
    list_display = ("army_list", "unit", "model_count", "points","enhancement", "is_warlord" ,"available_stratagems")
    list_filter = ("army_list", "unit")

    def points(self, obj):
        return obj.get_total_points()

    def available_stratagems(self, obj):
        return ", ".join(strat.name for strat in obj.get_valid_strats())