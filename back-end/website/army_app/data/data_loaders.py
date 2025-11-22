import csv
from django.core.exceptions import ValidationError
# This is in the dependancy order
from army_app.models import KeyWord, Ability, AbilityEffect, Faction, Detachment, Enhancement, Stratagem
from army_app.models import Weapon
from army_app.models import Unit, UnitPointBracket
from army_app.models import Leadership

def keyword_handler(keywords, model_class, row):
    """
    Given a semicolon-separated string of keywords, return list of KeyWord objects
    """
    keyword_objs = []
    if hasattr(model_class, keywords) and keywords in row and row[keywords].strip():
        keyword_objs = [
            KeyWord.objects.get_or_create(name=k.strip())[0] 
            for k in row[keywords].split(";") if k.strip()
        ]
    return keyword_objs


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
                # Pull out M2M fields for post-save binding
                m2m_fields = {
                    "or_keywords": keyword_handler("or_keywords", model_class, row),
                    "and_keywords": keyword_handler("and_keywords", model_class, row),
                    "not_keywords": keyword_handler("not_keywords", model_class, row),
                    "co_leaders": kwargs.pop("co_leaders", []),
                    "abilities": kwargs.pop("abilities", []),
                    "wargear_abilities": kwargs.pop("wargear_abilities", []),
                    "ranged_weapons": kwargs.pop("ranged_weapons", []),
                    "melee_weapons": kwargs.pop("melee_weapons", []),
                }

                # Validate temp instance
                unique_fields = [
                    field.name for field in model_class._meta.fields if field.unique
                ]
                temp = model_class(**kwargs)
                temp.full_clean(exclude=unique_fields)  # skip pk validation

                # Create and save obj
                obj, _ = model_class.objects.update_or_create(id=row["id"], defaults=kwargs)
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

def load_abilities(csv_path):
    def row_to_abilities_kwargs(row):
        errors = []

        return errors, {
            "name" : row["name"],
            "ability_type" : row["ability_type"]
        }
    return load_model(Ability, csv_path, row_to_abilities_kwargs)

def load_ability_effects(csv_path):
    def row_to_ability_effects_kwargs(row):
        errors = []
        try:
            ability = Ability.objects.get(name=row["ability"])
        except Ability.DoesNotExist:
            errors.append(f"Ability {row['ability']} not found for ability effect")
        
        if errors:
            return errors, None
        
        return errors, {
            "ability" : ability,
            "effect_description" : row["effect_description"],
        }
    return load_model(AbilityEffect, csv_path, row_to_ability_effects_kwargs)

def load_factions(csv_path):
    def row_to_faction_kwargs(row):
        errors = []
        abilities = []
        
        # Collect abilities and validate them
        if "abilities" in row and row["abilities"].strip():
            # Grab ability names
            ability_names = [name.strip() for name in row["abilities"].split(";") if name.strip()]
            # Grab abilities themselves, add abilities not found
            for name in ability_names:
                try:
                    ability = Ability.objects.get(name=name)
                    abilities.append(ability)
                except Ability.DoesNotExist:
                    errors.append(f"Ability {name} does not exist in DB")

        if errors:
            return errors, None

        return errors, {
            "name" : row["name"],
            "abilities" : abilities,
        }
    return load_model(Faction, csv_path, row_to_faction_kwargs)

def load_detachments(csv_path):
    def row_to_detachment_kwargs(row):
        errors = []
        abilities = []
        try:
            faction = Faction.objects.get(name=row["faction"])
        except Faction.DoesNotExist:
            errors.append(f"Faction {row['faction']} not found for detachment {row['name']}")
        
        # Collect abilities and validate them
        if "abilities" in row and row["abilities"].strip():
            # Grab ability names
            ability_names = [name.strip() for name in row["abilities"].split(";") if name.strip()]
            # Grab abilities themselves, add abilities not found
            for name in ability_names:
                try:
                    ability = Ability.objects.get(name=name)
                    abilities.append(ability)
                except Ability.DoesNotExist:
                    errors.append(f"Ability {name} does not exist in DB")

        if errors:
            return errors, None
        
        return errors, {
            "faction" : faction,
            "name" : row["name"],
            "abilities" : abilities,
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

def load_weapons(csv_path):
    def row_to_weapons_kwargs(row):
        errors = []
        abilities = []

        # Collect abilities and validate them
        if "abilities" in row and row["abilities"].strip():
            # Grab ability names
            ability_names = [name.strip() for name in row["abilities"].split(";") if name.strip()]
            # Grab abilities themselves, add abilities not found
            for name in ability_names:
                try:
                    ability = Ability.objects.get(name=name)
                    abilities.append(ability)
                except Ability.DoesNotExist:
                    errors.append(f"Ability {name} does not exist in DB")

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
            "abilities" : abilities,
        }
    return load_model(Weapon, csv_path, row_to_weapons_kwargs)

def load_units(csv_path):
    def row_to_units_kwargs(row):
        errors = []
        ranged_weapons = []
        melee_weapons = []
        abilities = []
        wargear_abilities = []

        try:
            faction = Faction.objects.get(name=row["faction"])
        except Faction.DoesNotExist:
            errors.append(f"Faction {row['faction']} not found for detachment {row['name']}")
        
        # Collect weapons and validate them
        if "ranged_weapons" in row and row["ranged_weapons"].strip():
            ranged_weapon_names = [name.strip() for name in row["ranged_weapons"].split(";") if name.strip()]
            for name in ranged_weapon_names:
                try:
                    weapon = Weapon.objects.get(name=name)
                    ranged_weapons.append(weapon)
                except Weapon.DoesNotExist:
                    errors.append(f"Weapon {name} does not exist in DB")

        if "melee_weapons" in row and row["melee_weapons"].strip():
            melee_weapon_names = [name.strip() for name in row["melee_weapons"].split(";") if name.strip()]
            for name in melee_weapon_names:
                try:
                    weapon = Weapon.objects.get(name=name)
                    melee_weapons.append(name)
                except Weapon.DoesNotExist:
                    errors.append(f"Weapon {name} does not exist in DB")
            
        # Collect abilities and validate them
        if "abilities" in row and row["abilities"].strip():
            ability_names = [name.strip() for name in row["abilities"].split(";") if name.strip()]
            # Grab abilities themselves, add abilities not found
            for name in ability_names:
                try:
                    ability = Ability.objects.get(name=name)
                    abilities.append(ability)
                except Ability.DoesNotExist:
                    errors.append(f"Ability {name} does not exist in DB")

        # Collect wargear_abilities and validate them
        if "wargear_abilities" in row and row["wargear_abilities"].strip():
            wargear_ability_names = [name.strip() for name in row["wargear_abilities"].split(";") if name.strip()]
            # Grab abilities themselves, add abilities not found
            for name in wargear_ability_names:
                try:
                    ability = Ability.objects.get(name=name)
                    wargear_abilities.append(ability)
                except Ability.DoesNotExist:
                    errors.append(f"Ability {name} does not exist in DB")
        
        if errors: 
            return errors, None

        return errors, {
            "faction" : faction,
            "name" : row["name"],
            "movement" : row["movement"],
            "toughness" : row["toughness"],
            "armour_save" : row["armour_save"],
            "wounds" : row["wounds"],
            "leadership" : row["leadership"],
            "objective_control" : row["objective_control"],
            "invulnerable_save" : row["invulnerable_save"],
            "ranged_weapons" : ranged_weapons,
            "melee_weapons" : melee_weapons,
            "wargear_options" : row["wargear_options"],
            "abilities" : abilities,
            "wargear_abilities" : wargear_abilities,
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