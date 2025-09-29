import logging
from pathlib import Path
import os
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
# In dependency order
from army_app.data import load_factions, load_detachments, load_enhancements, load_stratagems, load_abilities
from army_app.data import load_weapons 
from army_app.data import load_units, load_unit_point_brackets, load_data_sheet
from army_app.data import load_leadership

class Command(BaseCommand):
    help = "Validate CSV data before migration"

    def handle(self, *args, **options):
        loaders = [
            ("Factions", "data/factions.csv", load_factions),
            ("Detachments", "data/detachments.csv", load_detachments),
            ("Enhancements", "data/enhancements.csv", load_enhancements),
            ("Stratagems", "data/stratagems.csv", load_stratagems),
            ("Abilities", "data/abilities.csv", load_abilities),
            ("Weapons", "data/weapons.csv", load_weapons),
            ("Units", "data/units.csv", load_units),
            ("Unit Point Brackets", "data/unit_point_brackets.csv", load_unit_point_brackets),
            ("Datasheets", "data/datasheets", load_data_sheet),
            ("Leadership", "data/leadership.csv", load_leadership),
        ]
        # Setup logger from settings.py
        BASE_DIR = Path(__file__).resolve().parent.parent
        LOG_DIR = os.path.join(BASE_DIR, "logs")
        logger = logging.getLogger("validate_data")
        logger.setLevel(logging.INFO)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info("=" * 80)
        logger.info(f"Starting data validation run at {timestamp}")
        logger.info("=" * 80)

        # Flag for exit code
        all_errors = []
        # Stats for successful validations
        successful_validations = []

        for name, path, loader in loaders:
            objs, errors = loader(path)
            # Check if errors exist
            if errors:
                logger.error(f"Validation failed - {name}: {len(errors)} error(s) found...")
                for err in errors:
                    logger.error(err)
                all_errors.extend(errors)
            else:
                logger.info(f"OK: {name} validation completed")
                successful_validations.extend(objs)
            
        if all_errors:
            logger.error(f"Validation failed with {len(all_errors)} errors(s) found")
            logger.info(f"Logs saved in {LOG_DIR}")
            logger.info("=" * 80)
            # Exit with Django Command error - CI/CD will see failure like exit(1)
            raise CommandError(f"{len(all_errors)} errors found during validation")
        else:
            logger.info(f"OK: Validation complete with {len(successful_validations)} successful validations")
            logger.info(f"Logs saved to {LOG_DIR}")
            logger.info("=" * 80)