from django.contrib import admin
from army_app.models import KeyWord, Faction, Detachment, Enhancement, Stratagem
from army_app.models import Unit, UnitPointBracket, DataSheet
from army_app.models import Leadership
from army_app.models import ArmyList, ArmyListEntry, AssignedLeader

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

@admin.register(Leadership)
class LeadershipAdmin(admin.ModelAdmin):
    list_display = ("leader", "attached_unit")
    search_fields = ("leader__name",)
    list_filter = ("leader__faction",)
    ordering = ("leader__name",)

@admin.register(UnitPointBracket)
class UnitPointBracketAdmin(admin.ModelAdmin):
    list_display = ("unit", "points")
    # Search fields expect columns, so double underscore
    search_fields = ("unit__name",)
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
    
@admin.register(AssignedLeader)
class AssignedLeaderAdmin(admin.ModelAdmin):
    list_display = ("army_list", "leader_entry_display", "entry_display", "possible_leaders")
    readonly_fields = ("possible_leaders",)
    list_filter = ("entry__army_list",)

    def army_list(self, obj):
        return obj.entry.army_list
    
    def leader_entry_display(self, obj):
        return f"{obj.leader_entry.unit} [Entry {obj.leader_entry.id}]"
    
    def entry_display(self, obj):
        return f"{obj.entry.unit} [Entry {obj.entry.id}]"
    
    army_list.short_description = "Army List"
    leader_entry_display.short_description = "Leader"
    entry_display.short_description = "Follower"

    def possible_leaders(self, obj):
        if not obj.entry:
            return "-"
        all_leaders = obj.entry.get_all_leadership_options()
        return ", ".join(leader.leader.name for leader in all_leaders)
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "leader_entry" and getattr(request, "_obj_", None):
            valid_leaders = request._obj_.entry.get_available_leadership()
            kwargs["queryset"] = valid_leaders
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def get_form(self, request, obj = None, **kwargs):
        request._obj_ = obj
        return super().get_form(request, obj, **kwargs)