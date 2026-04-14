import logging
import csv
import os
from datetime import datetime
from django.core.management.base import BaseCommand
from pathlib import Path
from army_app.models import Faction, Ability, AbilityEffect, Detachment, Enhancement, Stratagem
from army_app.models import Weapon, Unit, UnitPointBracket, Leadership
from .utils import get_version_folders

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
LOG_DIR = os.path.join(BASE_DIR, "logs")
 
 
# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
 
def _write(out_dir: Path, filename: str, headers: list[str], rows):
    """Write a single CSV file with quoting that matches the originals."""
    path = out_dir / filename
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow(headers)
        for row in rows:
            writer.writerow(row)
    return path
 
 
def _join(qs, attr="name"):
    """Semicolon-join a queryset by a string attribute."""
    return ";".join(getattr(obj, attr) for obj in qs)
 
 
# ---------------------------------------------------------------------------
# Per-model dumpers
# (headers and field order match the loaders in data_loaders.py exactly)
# ---------------------------------------------------------------------------
 
def dump_abilities(out_dir: Path) -> int:
    """
    Loader expects: id, name, ability_type
    Original CSV also has: description, keywords, restricted_keywords
    We preserve those extra columns so the file stays compatible with the
    Google Sheet structure (even though the loader currently ignores them).
    """
    headers = ["id", "name", "ability_type",]
    rows = []
    for obj in Ability.objects.order_by("id"):
        rows.append([
            obj.id,
            obj.name,
            obj.ability_type,
        ])
    _write(out_dir, "abilities.csv", headers, rows)
    return len(rows)
 
 
def dump_ability_effects(out_dir: Path) -> int:
    """
    Loader expects: ability (name), effect_description, keyword_expression
    """
    headers = ["id", "ability", "effect_description", "keyword_expression"]
    rows = []
    for obj in AbilityEffect.objects.select_related("ability").order_by("id"):
        rows.append([
            obj.id,
            obj.ability.name,
            obj.effect_description,
            obj.keyword_expression,
        ])
    _write(out_dir, "ability_effects.csv", headers, rows)
    return len(rows)
 
 
def dump_factions(out_dir: Path) -> int:
    """
    Loader expects: id, name, abilities (semicolon-separated ability names)
    Original CSV had extra empty columns — we skip those.
    """
    headers = ["id", "name", "abilities"]
    rows = []
    for obj in Faction.objects.prefetch_related("abilities").order_by("id"):
        rows.append([
            obj.id,
            obj.name,
            _join(obj.abilities.order_by("name")),
        ])
    _write(out_dir, "factions.csv", headers, rows)
    return len(rows)
 
 
def dump_detachments(out_dir: Path) -> int:
    """
    Loader expects: id, faction (name), name, abilities (semicolon-separated)
    """
    headers = ["id", "faction", "name", "abilities"]
    rows = []
    for obj in (
        Detachment.objects
        .select_related("faction")
        .prefetch_related("abilities")
        .order_by("id")
    ):
        rows.append([
            obj.id,
            obj.faction.name,
            obj.name,
            _join(obj.abilities.order_by("name")),
        ])
    _write(out_dir, "detachments.csv", headers, rows)
    return len(rows)
 
 
def dump_enhancements(out_dir: Path) -> int:
    """
    Loader expects: id, detachment (name), name, description, points,
                    keyword_expression
    Original CSV also has: keywords, restricted_keywords columns.
    """
    headers = [
        "id", "detachment", "name", "description",
        "points", "keyword_expression",
    ]
    rows = []
    for obj in (
        Enhancement.objects
        .select_related("detachment")
        .order_by("id")
    ):
        rows.append([
            obj.id,
            obj.detachment.name,
            obj.name,
            obj.description,
            obj.points,
            obj.keyword_expression,
        ])
    _write(out_dir, "enhancements.csv", headers, rows)
    return len(rows)
 
 
def dump_stratagems(out_dir: Path) -> int:
    """
    Loader expects: id, detachment (name, may be blank), name, description,
                    cost, keyword_expression
    Original CSV also has: keywords, restricted_keywords columns.
    """
    headers = [
        "id", "detachment", "name", "when", "target",
        "effect", "restrictions", "cost", "keyword_expression",
    ]
    rows = []
    for obj in (
        Stratagem.objects
        .select_related("detachment")
        .order_by("id")
    ):
        rows.append([
            obj.id,
            obj.detachment.name if obj.detachment else "",
            obj.name,
            obj.when,
            obj.target,
            obj.effect,
            obj.restrictions,
            obj.cost,
            obj.keyword_expression,
        ])
    _write(out_dir, "stratagems.csv", headers, rows)
    return len(rows)
 
 
def dump_weapons(out_dir: Path) -> int:
    """
    Loader expects: id, name, type, range, attacks, skill, strength, ap,
                    damage, abilities (semicolon-separated ability names)
    """
    headers = [
        "id", "name", "type", "range", "attacks",
        "skill", "strength", "ap", "damage", "abilities",
    ]
    rows = []
    for obj in Weapon.objects.prefetch_related("abilities").order_by("id"):
        rows.append([
            obj.id,
            obj.name,
            obj.weapon_type,
            obj.weapon_range or "",
            obj.attacks,
            obj.skill,
            obj.strength,
            obj.ap,
            obj.damage,
            _join(obj.abilities.order_by("name")),
        ])
    _write(out_dir, "weapons.csv", headers, rows)
    return len(rows)
 
 
def dump_units(out_dir: Path) -> int:
    """
    Loader expects: id, faction (name), name, movement, toughness,
                    armour_save, wounds, ld, objective_control,
                    invulnerable_save, ranged_weapons, melee_weapons,
                    wargear_options, abilities, wargear_abilities
    Original CSV only had: id, faction, name, keywords — the extra stat
    columns were added in migration 0005.  We dump all current fields.
    """
    headers = [
        "id", "faction", "name", "keywords",
        "movement", "toughness", "armour_save", "wounds",
        "ld", "objective_control", "invulnerable_save",
        "ranged_weapons", "melee_weapons", "wargear_options",
        "abilities", "wargear_abilities",
    ]
    rows = []
    for obj in (
        Unit.objects
        .select_related("faction")
        .prefetch_related(
            "keywords", "ranged_weapons", "melee_weapons",
            "abilities", "wargear_abilities",
        )
        .order_by("id")
    ):
        rows.append([
            obj.id,
            obj.faction.name,
            obj.name,
            _join(obj.keywords.order_by("name")), #We only grab keywords from this model as Unit will be the only source of truth for keywords in the future
            obj.movement,
            obj.toughness,
            obj.armour_save,
            obj.wounds,
            obj.ld,
            obj.objective_control,
            obj.invulnerable_save or "",
            _join(obj.ranged_weapons.order_by("name")),
            _join(obj.melee_weapons.order_by("name")),
            obj.wargear_options,
            _join(obj.abilities.order_by("name")),
            _join(obj.wargear_abilities.order_by("name")),
        ])
    _write(out_dir, "units.csv", headers, rows)
    return len(rows)
 
 
def dump_unit_point_brackets(out_dir: Path) -> int:
    """
    Loader expects: id, unit (name), min_models, max_models, points
    """
    headers = ["id", "unit", "min_models", "max_models", "points"]
    rows = []
    for obj in (
        UnitPointBracket.objects
        .select_related("unit")
        .order_by("unit__name", "min_models")
    ):
        rows.append([
            obj.id,
            obj.unit.name,
            obj.min_models,
            obj.max_models,
            obj.points,
        ])
    _write(out_dir, "unit_point_brackets.csv", headers, rows)
    return len(rows)
 
 
def dump_leadership(out_dir: Path) -> int:
    """
    Loader expects: id, leader (unit name), attached_unit (unit name),
                    co_leaders (semicolon-separated unit names), keywords
    Note: the loader uses 'attached_unit' but the model field was renamed
    to 'attachable_unit' in migration 0005.
    """
    headers = ["id", "leader", "attached_unit", "co_leaders", "keywords"]
    rows = []
    for obj in (
        Leadership.objects
        .select_related("leader", "attachable_unit")
        .prefetch_related("co_leaders", "keywords")
        .order_by("id")
    ):
        rows.append([
            obj.id,
            obj.leader.name,
            obj.attachable_unit.name,
            _join(obj.co_leaders.order_by("name")),
            _join(obj.keywords.order_by("name")),
        ])
    _write(out_dir, "leadership.csv", headers, rows)
    return len(rows)
 
 
# ---------------------------------------------------------------------------
# Management command
# ---------------------------------------------------------------------------
 
DUMPERS = [
    ("Abilities",            "abilities.csv",           dump_abilities),
    ("AbilityEffects",       "ability_effects.csv",     dump_ability_effects),
    ("Factions",             "factions.csv",            dump_factions),
    ("Detachments",          "detachments.csv",         dump_detachments),
    ("Enhancements",         "enhancements.csv",        dump_enhancements),
    ("Stratagems",           "stratagems.csv",          dump_stratagems),
    ("Weapons",              "weapons.csv",             dump_weapons),
    ("Units",                "units.csv",               dump_units),
    ("UnitPointBrackets",    "unit_point_brackets.csv", dump_unit_point_brackets),
    ("Leadership",           "leadership.csv",          dump_leadership),
]
 
 
class Command(BaseCommand):
    help = "Dump current DB state to a versioned CSV folder (reverse of load_data)"
 
    def add_arguments(self, parser):
        parser.add_argument(
            "--output-dir",
            type=str,
            default=None,
            help=(
                "Override the output folder name (relative to data/).  "
                "Defaults to the current timestamp."
            ),
        )
        parser.add_argument(
            "--model",
            type=str,
            default=None,
            help=(
                "Dump only a specific model.  "
                "Choices: abilities, ability_effects, factions, detachments, "
                "enhancements, stratagems, weapons, units, "
                "unit_point_brackets, leadership"
            ),
        )
 
    def handle(self, *args, **options):
        logger = logging.getLogger("download_csv")
        logger.setLevel(logging.INFO)
 
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        folder_name = options["output_dir"] or timestamp
        out_dir = DATA_DIR / folder_name
        out_dir.mkdir(parents=True, exist_ok=True)
 
        model_filter = options["model"]
 
        logger.info("=" * 80)
        logger.info(f"Starting DB dump at {timestamp}")
        logger.info(f"Output directory: {out_dir}")
        logger.info("=" * 80)
 
        total = 0
        errors = []
 
        for label, filename, dumper in DUMPERS:
            # honour --model filter (match on filename stem or label)
            if model_filter:
                stem = filename.replace(".csv", "")
                if model_filter.lower() not in (stem.lower(), label.lower()):
                    continue
 
            try:
                count = dumper(out_dir)
                logger.info(f"OK: {label} — {count} row(s) written to {filename}")
                total += count
            except Exception as exc:
                msg = f"FAIL: {label} — {exc}"
                logger.error(msg)
                errors.append(msg)
 
        logger.info("=" * 80)
        if errors:
            logger.error(
                f"Dump completed with {len(errors)} error(s). "
                f"{total} total rows written."
            )
            for e in errors:
                logger.error(e)
        else:
            # Delete data directories only if no errors occurred
            # Manage number of versions to keep
            max_versions = 3
            version_folders = get_version_folders(DATA_DIR)
            if len(version_folders) > max_versions:
                to_delete = version_folders[:-max_versions]
                for folder in to_delete:
                    for file in folder.iterdir():
                        file.unlink()
                    folder.rmdir()
                    logger.warning(f"Deleted old version folder: {folder.name}")
            logger.info(
                f"Dump complete — {total} total rows written to {out_dir}"
            )
        logger.info("=" * 80)