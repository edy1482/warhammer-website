import csv
from django.core.exceptions import ValidationError
# This is in the dependancy order
from army_app.models import KeyWord, Ability, Faction, Detachment, Enhancement, Stratagem
from army_app.models import Weapon
from army_app.models import Unit, UnitPointBracket, DataSheet
from army_app.models import Leadership

def load_model(model_class, csv_path, row_to_kwargs):
    """
    Generic CSV loader + validator for army_app models
    Must be called within transaction.atomic block for easy rollback
    Handles ManyToMany Keyword column automatically
    """
    errors, saved_objs = [], []
    with open(csv_path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=1):
            # Build kwargs for model init
            row_errors, kwargs = row_to_kwargs(row)
            if row_errors:
                for err in row_errors:
                    errors.append(f"{model_class} Error - Row {idx}: {err}")
                continue # skip creating this object
            
            try:
                # Handle keywords if present
                keyword_objs = []
                if hasattr(model_class, "keywords") and "keywords" in row and row["keywords"].strip():
                    keyword_objs = [
                        KeyWord.objects.get_or_create(name=k.strip())[0] 
                        for k in row["keywords"].split(";") if k.strip()
                    ]

                # Pull out M2M fields for post-save binding
                m2m_fields = {
                    "keywords": keyword_objs,
                    "co_leaders": kwargs.pop("co_leaders", []),
                    "abilities": kwargs.pop("abilities", []),
                    "wargear_abilities": kwargs.pop("wargear_abilities", []),
                    "ranged_weapons": kwargs.pop("ranged_weapons", []),
                    "melee_weapons": kwargs.pop("melee_weapons", []),
                }

                # Create instance, validate and then save
                obj = model_class(**kwargs)
                obj.id = row["id"] or None
                obj.full_clean()
                obj.save()

                # Handle M2M relationships
                for field_name, related_objs in m2m_fields.items():
                    if hasattr(obj, field_name) and related_objs:
                        getattr(obj, field_name).set(related_objs)

                saved_objs.append(obj)
                
            except ValidationError as v_err:
                errors.append(f"{model_class} Validation Error - Row {idx}: {v_err}")
            except Exception as err:
                errors.append(f"{model_class} Unexpected Error - Row {idx}: {err}")
    return errors, saved_objs

def load_factions(csv_path):
    def row_to_faction_kwargs(row):
        errors = []

        return errors, {
            "name" : row["name"],
            "rule_name" : row["rule_name"],
            "rule_description" : row["rule_description"],
        }
    return load_model(Faction, csv_path, row_to_faction_kwargs)

def load_detachments(csv_path):
    def row_to_detachment_kwargs(row):
        errors = []
        try:
            faction = Faction.objects.get(name=row["faction"])
        except Faction.DoesNotExist:
            errors.append(f"Faction {row['faction']} not found for detachment {row['name']}")
            return errors, None
        
        return errors, {
            "faction" : faction,
            "name" : row["name"],
            "description" : row["description"],
        }
    return load_model(Detachment, csv_path, row_to_detachment_kwargs)

def load_enhancements(csv_path):
    def row_to_enhancement_kwargs(row):    
        errors = []

        try:
            detachment = Detachment.objects.get(name=row["detachment"])
        except Detachment.DoesNotExist:
            errors.append(f"Detachment {row['detachment']} not found for enhancement {row['name']}")
            return errors, None
        
        return errors, {
            "detachment" : detachment,
            "name" : row["name"],
            "description" : row["description"],
            "points" : row["points"],
        }
    return load_model(Enhancement, csv_path, row_to_enhancement_kwargs)

def load_stratagems(csv_path):
    def row_to_stratagems_kwargs(row):
        errors = []
        
        detachment_name = row["detachment"].strip()
        detachment = None
        if detachment_name:
            try:
                detachment = Detachment.objects.get(name=row["detachment"])
            except Detachment.DoesNotExist:
                errors.append(f"Detachment {row['detachment']} not found for enhancement {row['name']}")
                return errors, None
        
        return errors, {
            "detachment" : detachment,
            "name" : row["name"],
            "description" : row["description"],
            "cost" : row["cost"],
        }
    return load_model(Stratagem, csv_path, row_to_stratagems_kwargs)

def load_abilities(csv_path):
    def row_to_abilities_kwargs(row):
        errors = []

        return errors, {
            "name" : row["name"],
            "description" : row["description"],
        }
    return load_model(Ability, csv_path, row_to_abilities_kwargs)

def load_weapons(csv_path):
    def row_to_weapons_kwargs(row):
        errors = []
        missing = []
        ability_names = []

        # Collect abilities and validate them
        if "abilities" in row and row["abilities"].strip():
            ability_names = [name.strip() for name in row["abilities"].split(";") if name.strip()]
            missing = [name for name in ability_names if not Ability.objects.filter(name=name).exists()]
        
        if missing:
            errors.append(f"Weapon(s) not found: {', '.join(missing)}")

        if errors:
            return errors, None
            
        return errors, {
            "name" : row["name"],
            "weapon_type" : row["type"],
            "weapon_range" : row["range"],
            "attacks" : row["attacks"],
            "skill" : row["skill"],
            "strength" : row["strength"],
            "ap" : row["ap"],
            "damage" : row["damage"],
            "abilities" : ability_names,
        }
    return load_model(Weapon, csv_path, row_to_weapons_kwargs)

def load_units(csv_path):
    def row_to_units_kwargs(row):
        errors = []

        try:
            faction = Faction.objects.get(name=row["faction"])
        except Faction.DoesNotExist:
            errors.append(f"Faction {row['faction']} not found for detachment {row['name']}")
            return errors, None

        return errors, {
            "faction" : faction,
            "name" : row["name"],
        }
    return load_model(Unit, csv_path, row_to_units_kwargs)

def load_unit_point_brackets(csv_path):
    def row_to_brackets_kwargs(row):
        errors = []
        try:
            unit = Unit.objects.get(name=row["unit"])
        except Unit.DoesNotExist:
            errors.append(f"Unit {row['unit']} not found")

        if errors:
            return errors, None
        
        return errors, {
            "unit" : unit,
            "min_models" : row["min_models"],
            "max_models" : row["max_models"],
            "points" : row["points"],
        }
    return load_model(UnitPointBracket, csv_path, row_to_brackets_kwargs)

def load_data_sheet(csv_path):
    def row_to_data_sheet_kwargs(row):
        errors = []

        try:
            unit = Unit.objects.get(name=row["unit"])
        except Unit.DoesNotExist:
            errors.append(f"Unit {row['unit']} not found")

        missing = []

        # Collect weapons and validate them
        if "ranged_weapons" in row and row["ranged_weapons"].strip():
            ranged_weapon_names = [name.strip() for name in row["ranged_weapons"].split(";") if name.strip()]
            missing += [name for name in ranged_weapon_names if not Weapon.objects.filter(name=name).exists()]

        if "melee_weapons" in row and row["melee_weapons"].strip():
            melee_weapon_names = [name.strip() for name in row["melee_weapons"].split(";") if name.strip()]
            missing += [name for name in melee_weapon_names if not Weapon.objects.filter(name=name).exists()]

        # Collect abilities and validate them
        if "abilities" in row and row["abilities"].strip():
            ability_names = [name.strip() for name in row["abilities"].split(";") if name.strip()]
            missing += [name for name in ability_names if not Ability.objects.filter(name=name).exists()]

        # Collect wargear_abilities and validate them
        if "wargear_abilities" in row and row["wargear_abilities"].strip():
            wargear_ability_names = [name.strip() for name in row["wargear_abilities"].split(";") if name.strip()]
            missing += [name for name in wargear_ability_names if not Ability.objects.filter(name=name).exists()]

        if missing:
            errors.append(f"Objects not found: {', '.join(missing)}")
        
        if errors:
            return errors, None
        
        return errors, {
            "unit" : unit,
            "movement" : row["movement"],
            "toughness" : row["toughness"],
            "armour_save" : row["armour_save"],
            "wounds" : row["wounds"],
            "leadership" : row["leadership"],
            "objective_control" : row["objective_control"],
            "invulnerable_save" : row["invulnerable_save"],
            "ranged_weapons" : ranged_weapon_names,
            "melee_weapons" : melee_weapon_names,
            "wargear_options" : row["wargear_options"],
            "abilities" : ability_names,
            "wargear_abilities" : wargear_ability_names,
        }
    return load_model(DataSheet, csv_path, row_to_data_sheet_kwargs)  

def load_leadership(csv_path):
    def row_to_leadership(row):
        errors = []

        try:
            leader = Unit.objects.get(name=row["leader"])
        except Unit.DoesNotExist:
            errors.append(f"Leader unit {row['leader']} not found")
        
        try:
            attached_unit = Unit.objects.get(name=row["attached_unit"]) 
        except Unit.DoesNotExist:
            errors.append(f"Attached unit {row['attached_unit']} not found")

        # Collect co_leaders and validate them
        if "co_leaders" in row and row["co_leaders"].strip():
            co_leader_names = [name.strip() for name  in row["co_leaders"].split(";") if name.strip()]
            missing = [name for name in co_leader_names if not Unit.objects.filter(name=name).exists()]
        
        if missing:
            errors.append(f"Co_leader unit(s) not found: {', '.join(missing)}")

        if errors:
            return errors, None

        return errors, {
            "leader" : leader,
            "attached_unit" : attached_unit,
            "co_leaders" : co_leader_names,
        }
    return load_model(Leadership, csv_path, row_to_leadership)