import csv
from django.core.exceptions import ValidationError
from django.db import IntegrityError
# This is in the dependancy order
from army_app.models import KeyWord, Phase, Ability, AbilityEffect, Faction, Detachment, Enhancement, Stratagem
from army_app.models import Weapon
from army_app.models import Unit, UnitPointBracket
from army_app.models import Leadership, Support
from django.db import transaction
from .utils import resolve_ability
from .row_builders import *

# TODO: make stratagem when field match with Phase model

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

def csv_rows(csv_path):
    with open(csv_path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))

def load_model(model_class, rows, row_to_kwargs, lookup_fields=None, outcomes=None):
    """
    rows: iterable of dicts (CSV rows or scraped rows)
    row_to_kwargs: model based function that turns either csv row or scraped data into dict
    lookup_fields: natural key, e.g. ("name",) or ("faction", "name"). None means use row["id"], as CSV.
    outcomes: optional list for scraped data, one tuple of (source_key, obj_or_None, error_or_None) is appended per row,
            so the caller can write ScrapedPageLoadResult rows after transaction finishes
    Handles ManyToMany Keyword column automatically
    """
    def record(label, obj, error):
        if outcomes is not None:
            outcomes.append((label, obj, error))

    errors, saved_objs = [], []
    unique_fields = [ field.name for field in model_class._meta.fields if field.unique]
    
    for idx, row in enumerate(rows, start=1):
        label = row.get("_source_key") or f"Row {idx}"
        # Build kwargs for model init
        row_errors, kwargs = row_to_kwargs(row)
        if row_errors:
            msgs = [f"{model_class} Error - {label}: {err}" for err in row_errors]
            errors.extend(msgs)
            record(label, None, "; ".join(row_errors))
            continue # skip creating this object
        
        try:
            with transaction.atomic():
            # Pull out M2M fields for post-save binding
                m2m_fields = {
                    "keywords": keyword_handler("keywords", model_class, row),
                    "co_leaders": kwargs.pop("co_leaders", []),
                    "phase" : kwargs.pop("phase", []),
                    "abilities": kwargs.pop("abilities", []),
                    "wargear_abilities": kwargs.pop("wargear_abilities", []),
                    "ranged_weapons": kwargs.pop("ranged_weapons", []),
                    "melee_weapons": kwargs.pop("melee_weapons", []),
                    "detachments" : kwargs.pop("detachments", []),
                }

                # Validate temp instance
                model_class(**kwargs).full_clean(validate_unique=False, validate_constraints=False)

                lookup = (
                    {f: kwargs[f] for f in lookup_fields}
                    if lookup_fields else {"id" : row["id"]}
                )

                # Create and save obj
                obj, _ = model_class.objects.update_or_create(**lookup, defaults=kwargs)
                obj.full_clean()

                # Handle M2M relationships
                for field_name, related_objs in m2m_fields.items():
                    if not hasattr(obj, field_name):
                        if related_objs:
                            raise AttributeError(f"{model_class.__name__} has no M2M field '{field_name}'")
                        continue
                    getattr(obj, field_name).set(related_objs)

            saved_objs.append(obj)
            record(label, obj, None)
            
        except ValidationError as v_err:
            errors.append(f"{model_class} Validation Error - Row {idx}: {v_err}")
            record(label, None, str(v_err))
        except IntegrityError as db_err:
            errors.append(f"{model_class} Conflict - {label}: violates a unique constraint ({db_err.__cause__ or db_err})")
            record(label, None, f"unique constraint: {db_err.__cause__ or db_err}")
        except Exception as err:
            errors.append(f"{model_class} Unexpected Error - Row {idx}: {err}")
            record(label, None, str(err))
    return errors, saved_objs

def load_phase(csv_path):
    return load_model(Phase, csv_rows(csv_path), row_to_phase_kwargs, lookup_fields=["name"])

def load_abilities(csv_path):
    return load_model(Ability, csv_rows(csv_path), row_to_abilities_kwargs, lookup_fields=["name", "value"])

def load_ability_effects(csv_path):
    return load_model(AbilityEffect, csv_rows(csv_path), row_to_ability_effects_kwargs, lookup_fields=["ability", "effect_description"])

def load_factions(csv_path):
    return load_model(Faction, csv_rows(csv_path), row_to_faction_kwargs, lookup_fields=["name"])

def load_detachments(csv_path):
    return load_model(Detachment, csv_rows(csv_path), row_to_detachment_kwargs, lookup_fields=["name", "faction"])

def load_enhancements(csv_path):
    return load_model(Enhancement, csv_rows(csv_path), row_to_enhancement_kwargs, lookup_fields=["name"])

def load_stratagems(csv_path):
    return load_model(Stratagem, csv_rows(csv_path), row_to_stratagems_kwargs, lookup_fields=["name"])

def load_weapons(csv_path):
    return load_model(Weapon, csv_rows(csv_path), row_to_weapons_kwargs, lookup_fields=["name"])

def load_units(csv_path):
    return load_model(Unit, csv_rows(csv_path), row_to_units_kwargs, lookup_fields=["name", "faction"])

def load_unit_point_brackets(csv_path):
    return load_model(UnitPointBracket, csv_rows(csv_path), row_to_brackets_kwargs, lookup_fields=["unit", "min_models", "max_models"])

def load_leadership(csv_path):
    return load_model(Leadership, csv_rows(csv_path), row_to_leadership, lookup_fields=["leader", "bodyguard_unit"])

def load_support(csv_path):
    return load_model(Support, csv_rows(csv_path), row_to_support, lookup_fields=["support", "bodyguard_unit"])