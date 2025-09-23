import logging
import os
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
# In dependency order
from army_app.data_loaders import load_factions, load_detachments, load_enhancements, load_stratagems
from army_app.data_loaders import load_abilities, load_weapons 
from army_app.data_loaders import load_units, load_unit_point_brackets, load_data_sheet
from army_app.data_loaders import load_leadership

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

        # Ensure log folder exists
        log_dir = os.path.join(os.getcwd(), "logs")
        os.makedirs(log_dir, exist_ok=True)

        # Timestamp the log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f"validate_data_{timestamp}.log")

        # Setup logger
        logger = logging.getLogger("validate_data")
        logger.setLevel(logging.INFO)

        # Add handlers
        if not logger.handlers:
            # File handler
            fh = logging.FileHandler(log_file)
            fh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
            logger.addHandler(fh)
            ch = logging.StreamHandler()
            ch.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))
            logger.addHandler(ch)
        
        # Flag for exit code
        all_errors = []
        # Stats for successful validations
        successful_validations = []

        logger.info("Starting data validation...")

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
            logger.info(f"Logs saved to {log_file}")
            # Exit with Django Command error - CI/CD will see failure like exit(1)
            raise CommandError(f"{len(all_errors)} errors found during validation")
        else:
            logger.info(f"OK: Validation complete with {len(successful_validations)} successful validations")
            logger.info(f"Logs saved to {log_file}")