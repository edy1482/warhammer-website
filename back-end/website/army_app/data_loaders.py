import csv
from django.core.exceptions import ValidationError
# This is in the dependancy order
from army_app.models import KeyWord, Faction, Detachment, Enhancement, Stratagem
from army_app.models import Unit, UnitPointBracket, DataSheet
from army_app.models import Leadership

def load_model(model_class, csv_path, row_to_kwargs):
    """
    Generic CSV loader + validator for army_app models
    Handles ManyToMany Keyword column automatically
    """
    errors, valid_objs = [], []
    with open(csv_path, newline="") as f:
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
                    kwargs["keywords"] = keyword_objs
                # Pull out co_leaders temporarily
                co_leaders = kwargs.pop("co_leaders", [])
                # Create instance without keywords (keywords can only be added after save)
                obj = model_class(**{key: value for key, value in kwargs.items() if key !="keywords"})
                # Validate
                obj.full_clean()
                # Add to list (w/ keywords)
                valid_objs.append((obj, kwargs.get("keywords", []), co_leaders))
            except ValidationError as v_err:
                errors.append(f"{model_class} Validation Error - Row {idx}: {v_err}")
            except Exception as err:
                errors.append(f"{model_class} Unexpected Error - Row {idx}: {err}")
    return errors, valid_objs

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
            errors.append(f"Faction {row["faction"]} not found for detachment {row["name"]}")
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
            errors.append(f"Detachment {row["detachment"]} not found for enhancement {row["name"]}")
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
                errors.append(f"Detachment {row["detachment"]} not found for enhancement {row["name"]}")
                return errors, None
        
        return errors, {
            "detachment" : detachment,
            "name" : row["name"],
            "description" : row["description"],
            "cost" : row["cost"],
        }
    return load_model(Stratagem, csv_path, row_to_stratagems_kwargs)

def load_units(csv_path):
    def row_to_units_kwargs(row):
        errors = []

        try:
            faction = Faction.objects.get(name=row["faction"])
        except Faction.DoesNotExist:
            errors.append(f"Faction {row["faction"]} not found for detachment {row["name"]}")
            return errors, None

        return errors, {
            "faction" : faction,
            "name" : row["name"],
            "min_models" : row["min_models"],
            "max_models" : row["max_models"],
            "points" : row["points"],
        }
    return load_model(Unit, csv_path, row_to_units_kwargs)

def load_leadership(csv_path):
    def row_to_leadership(row):
        errors = []

        try:
            leader = Unit.objects.get(name=row["leader"])
        except Unit.DoesNotExist:
            errors.append(f"Leader unit {row["leader"]} not found")
        
        try:
            attached_unit = Unit.objects.get(name=row["attached_unit"])
        except Unit.DoesNotExist:
            errors.append(f"Attached unit {row["attached_unit"]} not found")
        
        if errors:
            return errors, None
        
        kwargs = {
            "leader" : leader,
            "attached_unit" : attached_unit,
        }

        # Collect co_leaders and validate them
        if "co_leaders" in row and row["co_leaders"].strip():
            co_leader_names = [name.strip() for name  in row["co_leaders"].split(";") if name.strip()]
            missing = [name for name in co_leader_names if not Unit.objects.filter(name=name).exists()]
        
        if missing:
            errors.append(f"Co_leader unit(s) not found: {', '.join(missing)}")
            return errors, None
        
        # If co_leader names exist, store names for later Leadership linking
        kwargs["co_leaders"] = co_leader_names

        return errors, kwargs
    return load_model(Leadership, csv_path, row_to_leadership)