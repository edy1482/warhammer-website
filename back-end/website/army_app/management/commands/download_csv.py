import requests
import os
import logging
from datetime import datetime
from django.core.management.base import BaseCommand
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
SHEET_ID = "1hjo6Cel6e-nh7Yc4d5fXnPHtLopYh_uEYGemejXlzJU"
LOG_DIR = os.path.join(BASE_DIR, "logs")

SHEETS = {
    "abilities": (SHEET_ID, "Abilities"),
    "ability_effects": (SHEET_ID, "Ability Effects"),
    "factions": (SHEET_ID, "Factions"),
    "detachments": (SHEET_ID, "Detachments"),
    "enhancements": (SHEET_ID, "Enhancements"),
    "stratagems": (SHEET_ID, "Stratagems"),
    "weapons": (SHEET_ID, "Weapons"),
    "units": (SHEET_ID, "Units"),
    "unit_point_brackets": (SHEET_ID, "Unit Point Brackets"),
    "leadership": (SHEET_ID, "Leaderships"),
}

class Command(BaseCommand):
    help = "Download latest CSVs from Google Sheets"

    def handle(self, *args, **options):
        # Grab logger
        logger = logging.getLogger("download_csv")
        logger.setLevel(logging.INFO)
        # Write logger intro
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info("=" * 80)
        logger.info(f"Starting CSV downloads at {timestamp}")
        logger.info("=" * 80)
        
        version_dir = DATA_DIR / timestamp
        version_dir.mkdir(parents=True, exist_ok=True)
        for name, (sheet_id, tab) in SHEETS.items():
            url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={tab}"
            out_path = version_dir / f"{name}.csv"
            resp = requests.get(url)
            resp.raise_for_status()
            out_path.write_bytes(resp.content)
            logger.info(f"Updated {name}.csv")
        # Write logger outro
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info("=" * 80)
        logger.info(f"Finished CSV downloads at {timestamp}")
        logger.info("=" * 80)
        return