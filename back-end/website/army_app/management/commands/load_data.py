import logging
from pathlib import Path
import os
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.apps import apps
# In dependency order
from army_app.data import load_factions, load_detachments, load_enhancements, load_stratagems, load_abilities
from army_app.data import load_weapons 
from army_app.data import load_units, load_unit_point_brackets, load_data_sheet
from army_app.data import load_leadership
from .utils import get_latest_version, get_previous_version

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = os.path.join(BASE_DIR, "data")
LOG_DIR = os.path.join(BASE_DIR, "logs")

class Command(BaseCommand):
    help = "Validates, applies, or rolls back data from CSVs"

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--apply", action="store_true", help="Validate and save to DB")
        group.add_argument("--rollback", action="store_true", help="Rollback data to previous or specified version")
        parser.add_argument("--data_version", type=str, help="Version folder (timestamp or name)")

    def handle(self, *args, **options):
        # Setup logger from settings.py
        logger = logging.getLogger("validate_data")
        logger.setLevel(logging.INFO)

        # Write logger intro
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info("=" * 80)
        logger.info(f"Starting data load run at {timestamp}")
        logger.info("=" * 80)

        # Grab CSV folder (default to latest version if not given)
        version_dir = options.get("data_version") or get_latest_version(DATA_DIR)
        if not version_dir:
            logger.error("load_data command failed - No version folders found in directory")
            # Exit with Django Command error - CI/CD will see failure like exit(1)
            raise CommandError("No version folders found in directory")

        # Rollback (default to previous version if not given)
        if options["rollback"]:
            version_dir = options.get("data_version") or get_previous_version(DATA_DIR)
            if not version_dir:
                logger.error("load_data command failed - No previous version to rollback to")
                # Exit with Django Command error - CI/CD will see failure like exit(1)
                raise CommandError("No previous version to rollback to")
            logger.info(f"[Rollback] Starting rollback for version {version_dir}")
            self.rollback_version(version_dir)
            logger.info(f"Logs saved to {LOG_DIR}")
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            logger.info("=" * 80)
            logger.info(f"Ending rollback at {timestamp}")
            logger.info("=" * 80)
            return
        
        if options["--apply"]:
            logger.info(f"[Apply] Starting data load for version {version_dir}")
            self.load_from_version(version_dir)  
            # Write logger outro
            logger.info(f"Logs saved to {LOG_DIR}")
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            logger.info("=" * 80)
            logger.info(f"Ending data load run at {timestamp}")
            logger.info("=" * 80)
            return

    def get_loaders(self, version_dir):
        VERS_DIR = DATA_DIR / version_dir
        loaders = [
            ("Factions",  VERS_DIR / "factions.csv", load_factions),
            ("Detachments", VERS_DIR / "detachments.csv", load_detachments),
            ("Enhancements", VERS_DIR / "enhancements.csv", load_enhancements),
            ("Stratagems", VERS_DIR / "stratagems.csv", load_stratagems),
            ("Abilities", VERS_DIR / "abilities.csv", load_abilities),
            ("Weapons", VERS_DIR / "weapons.csv", load_weapons),
            ("Units", VERS_DIR / "units.csv", load_units),
            ("Unit Point Brackets", VERS_DIR / "unit_point_brackets.csv", load_unit_point_brackets),
            ("Datasheets", VERS_DIR / "datasheets.csv", load_data_sheet),
            ("Leadership", VERS_DIR / "leadership.csv", load_leadership),
        ]
        return loaders
    
    @transaction.atomic
    def load_from_version(self, version_dir):
        # Set up logger
        logger = logging.getLogger("load_data")
        loaders = self.get_loaders(version_dir)
        
        # Set up for stats/error handling
        all_errors = []
        successful_saves = []
        logger.info("Starting validation...")
        
        for name, path, loader in loaders:
            # Loader itself saves and sets m2m relationships
            errors, objs = loader(path)
            # Check if errors exist
            if errors:
                logger.error(f"FAIL: Validation failed - {name}: {len(errors)} error(s) found...")
                for err in errors:
                    logger.error(err)
                all_errors.extend(errors)
            else:
                # Save object into the DB
                logger.info(f"OK: {name} validation completed")
                successful_saves.extend(objs)
        
        # If errors, rollback the transaction, log it and exit
        if all_errors:
            transaction.set_rollback(True)
            logger.error(f"FAIL: Validation failed with {len(all_errors)} errors(s) found")
            logger.info(f"Logs saved in {LOG_DIR}")
            logger.info("=" * 80)
            # Exit with Django Command error - CI/CD will see failure like exit(1)
            raise CommandError(f"{len(all_errors)} errors found during validation")
        else:
            logger.info(f"OK: Validation complete with {len(successful_saves)} successful validations")

    def rollback_version(self, version_dir):
        logger = logging.getLogger("load_data")
        logger.info("Starting rollback...")
        confirm = input("⚠️  This will delete and reload data. Continue? [y/N]: ").strip().lower()
        if confirm not in {"y", "yes"}:
            logger.info("Rollback cancelled.")
            return

        target_models = [
            "KeyWord",
            "Factions",
            "Detachments",
            "Enhancements",
            "Stratagems",
            "Abilities",
            "Weapons",
            "Units",
            "Unit Point Brackets",
            "Datasheets",
            "Leadership",
        ].reverse()

        with transaction.atomic():
            # Clear all target_models
            for model_name in target_models:
                model_class = apps.get_model("army_app", model_name)
                deleted, _ = model_class.objects.all().delete()
                logger.info(f"Cleared {deleted} records from {model_name}")
        
            # Load from previous/specified version
            self.load_from_version(version_dir)

        logger.info(f"OK: Rollback to {version_dir} completed.")
        return