import json
from django.contrib import admin
from django.urls import path, reverse
from django.utils.safestring import mark_safe
from django.utils.html import format_html
from django.shortcuts import get_object_or_404, render
from army_app.models import ScrapedPage, KeyWord, KeyWordCondition, Ability, AbilityEffect, Faction, Detachment, Enhancement, Stratagem
from army_app.models import Weapon
from army_app.models import Unit, UnitPointBracket
from army_app.models import Leadership
from army_app.models import ArmyList, ArmyListEntry, AssignedLeader

@admin.register(ScrapedPage)
class ScrapedPageAdmin(admin.ModelAdmin):
    list_display = ("url", "status", "status_code", "scraped_at", "created_at")
    list_filter = ("status",)
    search_fields = ("url",)
    readonly_fields = ("html_content", "created_at", "updated_at")

@admin.register(KeyWord)
class KeyWordAdmin(admin.ModelAdmin):
    search_fields = ("name",)
    ordering = ("name",)

@admin.register(KeyWordCondition)
class KeyWordConditionAdmin(admin.ModelAdmin):
    readonly_fields = ("tree_display", "expression_display",)

    def tree_display(self, obj):
        tree = obj.render_tree()
        return mark_safe(f"<pre style='font-family:monospace'>{tree}</pre>")
    
    tree_display.short_description = "Condition Tree"

    def expression_display(self, obj):
        return obj.to_expression()

    # Only grab parent nodes
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(parent__isnull=True)
    
@admin.register(Ability)
class AbilityAdmin(admin.ModelAdmin):
    list_display = ("name", "ability_type",)
    search_fields = ("name",)
    list_filter = ("ability_type",)
    
@admin.register(AbilityEffect)
class AbilityEffectAdmin(admin.ModelAdmin):
    list_display = ("ability", "effect_description",)
    search_fields = ("ability__name", "effect_description",)
    list_filter = ("ability__ability_type",)
    
@admin.register(Faction)
class FactionAdmin(admin.ModelAdmin):
    list_display = ("name", "abilities__name",)
    search_fields = ("name", "abilities__name",)
    ordering = ("name",)

@admin.register(Detachment)
class DetachmentAdmin(admin.ModelAdmin):
    list_display = ("name", "faction")
    search_fields = ("name",)
    list_filter = ("faction",)
    ordering = ("faction",)

@admin.register(Stratagem)
class StratagemAdmin(admin.ModelAdmin):
    list_display = ("name", "detachment",)
    search_fields = ("name",)
    list_filter = ("detachment",)

@admin.register(Enhancement)
class EnhancementAdmin(admin.ModelAdmin):
    list_display = ("name", "detachment", "points",)
    search_fields = ("name",)
    list_filter = ("detachment__faction",)

@admin.register(Weapon)
class WeaponAdmin(admin.ModelAdmin):
    list_display = ("name", "weapon_type", "weapon_range", "attacks", "skill", "strength", "ap", "damage",)
    search_fields = ("name",)
    list_filter = ("weapon_type",)

@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ("name", "faction",)
    search_fields = ("name",)
    list_filter = ("faction", "keywords",)
    filter_horizontal = ("keywords",)
    ordering = ("name",)

@admin.register(Leadership)
class LeadershipAdmin(admin.ModelAdmin):
    list_display = ("leader", "attachable_unit")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "leader":
            kwargs["queryset"] = Unit.objects.filter(keywords__name__iexact="LEADER").distinct()
        elif db_field.name == "attachable_unit":
            kwargs["queryset"] = Unit.objects.exclude(keywords__name__iexact="LEADER").distinct()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "co_leaders":
            kwargs["queryset"] = Unit.objects.filter(keywords__name__iexact="LEADER").distinct()
        return super().formfield_for_manytomany(db_field, request, **kwargs)
    
    def get_form(self, request, obj = None, **kwargs):
        request._obj_ = obj
        return super().get_form(request, obj, **kwargs)

@admin.register(UnitPointBracket)
class UnitPointBracketAdmin(admin.ModelAdmin):
    list_display = ("unit", "points")
    # Search fields expect columns, so double underscore
    search_fields = ("unit__name",)
    list_filter = ("unit__faction",)

@admin.register(ArmyList)
class ArmyListAdmin(admin.ModelAdmin):
    list_display = ("user", "name", "faction", "detachment", "stratagem_graph_link")
    search_fields = ("name",)
    list_filter = ("faction", "detachment")
    readonly_fields = ("stratagem_graph_button",)

    def get_fields(self, request, obj=None):
        fields = list(super().get_fields(request, obj))
        # Only show the graph button once the ArmyList has been saved (has a pk)
        if obj and obj.pk and "stratagem_graph_button" not in fields:
            fields.append("stratagem_graph_button")
        elif not (obj and obj.pk) and "stratagem_graph_button" in fields:
            fields.remove("stratagem_graph_button")
        return fields

    def get_urls(self):
        custom_urls = [
            path(
                "<int:object_id>/stratagem-graph/",
                self.admin_site.admin_view(self.stratagem_graph_view),
                name="army_app_armylist_stratagem_graph",
            ),
        ]
        return custom_urls + super().get_urls()

    def stratagem_graph_link(self, obj):
        if not obj.pk:
            return "-"
        url = reverse("admin:army_app_armylist_stratagem_graph", args=[obj.pk])
        return format_html('<a class="button" href="{}">Stratagem graph</a>', url)
    stratagem_graph_link.short_description = "Unit ↔ stratagem graph"

    def stratagem_graph_button(self, obj):
        if not obj or not obj.pk:
            return "-"
        url = reverse("admin:army_app_armylist_stratagem_graph", args=[obj.pk])
        return format_html('<a class="button" href="{}" target="_blank">Open unit ↔ stratagem graph →</a>', url)
    stratagem_graph_button.short_description = "Stratagem graph"

    def stratagem_graph_view(self, request, object_id):
        """
        Renders a bipartite graph of every ArmyListEntry (unit) in this
        ArmyList against every Stratagem it can legally use, derived from
        ArmyListEntry.get_valid_strats() (CORE strats + detachment strats
        whose keywords match the unit's keywords).
        """
        army_list = get_object_or_404(ArmyList, pk=object_id)
        entries = (
            army_list.entries
            .select_related("unit")
            .order_by("unit__name")
        )

        nodes = []
        edges = []
        seen_strat_ids = set()

        for entry in entries:
            unit_node_id = f"unit-{entry.id}"
            nodes.append({
                "id": unit_node_id,
                "label": f"{entry.unit.name} [#{entry.id}]",
                "group": "unit",
            })

            valid_strats = entry.get_valid_strats().order_by("name")
            for strat in valid_strats:
                strat_node_id = f"strat-{strat.id}"
                is_core = strat.keywords.filter(name__iexact="CORE").exists()
                if strat.id not in seen_strat_ids:
                    seen_strat_ids.add(strat.id)
                    nodes.append({
                        "id": strat_node_id,
                        "label": strat.name,
                        "group": "stratagem",
                        "title": strat.effect[:300] if strat.effect else "",
                        "core": is_core,
                    })
                edges.append({
                    "from": unit_node_id,
                    "to": strat_node_id,
                    "core": is_core,
                })

        context = {
            **self.admin_site.each_context(request),
            "title": f"Unit \u2194 stratagem graph — {army_list}",
            "army_list": army_list,
            "opts": self.model._meta,
            "nodes_json": mark_safe(json.dumps(nodes)),
            "edges_json": mark_safe(json.dumps(edges)),
            "has_entries": entries.exists(),
        }
        return render(request, "admin/army_app/armylist/stratagem_graph.html", context)

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