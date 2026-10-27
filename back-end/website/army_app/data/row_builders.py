from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist

# This is in the dependancy order
from army_app.models import KeyWord, Phase, Ability, AbilityEffect, Faction, Detachment, Enhancement, Stratagem
from army_app.models import Weapon
from army_app.models import Unit, UnitPointBracket
from army_app.models import Leadership
from .utils import resolve_ability

def split_cell(row, column):
    """
    Semicolon-joined cell -> list of stripped names
    A blank cell gives []
    A missing column raises an error, so it fails loudly
    """
    try:
        raw = row[column]
    except KeyError:
        raise KeyError(f"column '{column}' is missing from row / CSV header") from None
    return [n.strip() for n in (raw or "").split(";") if n.strip()]

def by_name(model):
    """
    Get name from model
    """
    return lambda name: model.objects.get(name=name)

def resolve_all(names, resolver, label, errors):
    """
    Resolve each name, and append one message per failure to errors
    """
    objs = []
    for name in names:
        try:
            objs.append(resolver(name))
        except ObjectDoesNotExist:
            errors.append(f"{label} {name} does not exist in DB")
        except MultipleObjectsReturned:
            errors.append(f"{label} {name} matches more than one row in DB")
    return objs

def resolve_one(name, resolver, label, errors):
    objs = resolve_all([name], resolver, label, errors)
    return objs[0] if objs else None

def row_to_phase_kwargs(row):
        errors = []

        return errors, {
            "name" : row["phase_name"]
        }

def row_to_abilities_kwargs(row):
        errors = []

        return errors, {
            "name" : row["name"],
            "value" : row["value"],
            "ability_type" : row["ability_type"]
        }

def row_to_ability_effects_kwargs(row):
        errors = []

        ability = resolve_one(row["ability"], resolve_ability, "Ability", errors)
        phases = resolve_all(split_cell(row, "phase"), by_name(Phase), "Phase", errors)
        
        if errors:
            return errors, None
        
        return errors, {
            "ability" : ability,
            "phase" : phases,
            "effect_description" : row["effect_description"],
            "turn_scope" : row["turn"],
            "keyword_expression" : row["keyword_expression"],
        }

def row_to_faction_kwargs(row):
        errors = []
        
        abilities = resolve_all(split_cell(row, "abilities"), resolve_ability, "Ability", errors)

        if errors:
            return errors, None

        return errors, {
            "name" : row["name"],
            "abilities" : abilities,
        }

def row_to_detachment_kwargs(row):
        errors = []

        faction = resolve_one(row["faction"], by_name(Faction), "Faction", errors)
        abilities = resolve_all(split_cell(row, "abilities"), resolve_ability, "Ability", errors)

        if errors:
            return errors, None
        
        return errors, {
            "faction" : faction,
            "name" : row["name"],
            "abilities" : abilities,
        }

def row_to_enhancement_kwargs(row):    
        errors = []

        detachment = resolve_one(row["detachment"], by_name(Detachment), "Detachment", errors)        

        if errors:
            return errors, None
        
        return errors, {
            "detachment" : detachment,
            "name" : row["name"],
            "description" : row["description"],
            "points" : row["points"],
            "keyword_expression" : row["keyword_expression"],
        }

def row_to_stratagems_kwargs(row):
        errors = []

        phases = resolve_all(split_cell(row, "phase"), by_name(Phase), "Phase", errors)
        detachments = resolve_all(split_cell(row, "detachments"), by_name(Detachment), "Detachment", errors)

        if errors:
            return errors, None
        
        return errors, {
            "detachments" : detachments,
            "name" : row["name"],
            "phase" : phases,
            "turn_scope" : row["turn"],
            "when" : row["when"],
            "target" : row["target"],
            "effect" : row["effect"],
            "restrictions" : row["restrictions"],
            "cost" : row["cost"],
            "keyword_expression" : row["keyword_expression"],
        }

def row_to_weapons_kwargs(row):
        errors = []

        abilities = resolve_all(split_cell(row, "abilities"), resolve_ability, "Ability", errors)
        
        if errors:
            return errors, None
            
        return errors, {
            "name" : row["name"],
            "display_name" : row["display_name"],
            "weapon_type" : row["type"],
            "weapon_range" : row["range"],
            "attacks" : row["attacks"],
            "skill" : row["skill"],
            "strength" : row["strength"],
            "ap" : row["ap"],
            "damage" : row["damage"],
            "abilities" : abilities,
        }

def row_to_units_kwargs(row):
        errors = []
        wargear_abilities = []

        faction = resolve_one(row["faction"], by_name(Faction), "Faction", errors)
        abilities = resolve_all(split_cell(row, "abilities"), resolve_ability, "Ability", errors)
        wargear_abilities = resolve_all(split_cell(row, "wargear_abilities"), resolve_ability, "Wargear ability", errors)
        ranged_weapons = resolve_all(split_cell(row, "ranged_weapons"), by_name(Weapon), "Ranged weapon", errors)
        melee_weapons = resolve_all(split_cell(row, "melee_weapons"), by_name(Weapon), "Melee weapon", errors)
        
        if errors: 
            return errors, None

        return errors, {
            "faction" : faction,
            "name" : row["name"],
            "movement" : row["movement"],
            "toughness" : row["toughness"],
            "armour_save" : row["armour_save"],
            "wounds" : row["wounds"],
            "ld" : row["ld"],
            "objective_control" : row["objective_control"],
            "invulnerable_save" : row["invulnerable_save"],
            "ranged_weapons" : ranged_weapons,
            "melee_weapons" : melee_weapons,
            "wargear_options" : row["wargear_options"],
            "abilities" : abilities,
            "wargear_abilities" : wargear_abilities,
        }

def row_to_brackets_kwargs(row):
        errors = []
        unit = resolve_one(row["unit"], by_name(Unit), "Unit", errors)

        if errors:
            return errors, None
        
        return errors, {
            "unit" : unit,
            "min_models" : row["min_models"],
            "max_models" : row["max_models"],
            "points" : row["points"],
        }

def row_to_leadership(row):
        errors = []

        leader = resolve_one(row["leader"], by_name(Unit), "Leader unit", errors)
        bodyguard_unit = resolve_one(row["bodyguard_unit"], by_name(Unit), "Bodyguard unit", errors)

        if errors:
            return errors, None

        return errors, {
            "bodyguard_unit" : bodyguard_unit,
            "leader" : leader,
        }

def row_to_support(row):
     errors = []

     bodyguard_unit = resolve_one(row["bodyguard_unit"], by_name(Unit), "Bodyguard unit", errors)
     support = resolve_one(row["support"], by_name(Unit), "Support unit", errors)

     if errors:
        return errors, None

     return errors, {
          "bodyguard_unit" : bodyguard_unit,
          "support" : support,
    }