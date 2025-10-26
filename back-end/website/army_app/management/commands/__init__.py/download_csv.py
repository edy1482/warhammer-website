# army_app/management/commands/update_csvs_from_sheets.py
import requests
from datetime import datetime
from django.core.management.base import BaseCommand
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "army_app" / "data"
SHEET_ID = "1hjo6Cel6e-nh7Yc4d5fXnPHtLopYh_uEYGemejXlzJU"


SHEETS = {
    "factions": (SHEET_ID, "Factions"),
    "detachments": (SHEET_ID, "Detachments"),
    "enhancements": (SHEET_ID, "Enhancements"),
    "stratagems": (SHEET_ID, "Stratagems"),
    "abilities": (SHEET_ID, "Abilities"),
    "weapons": (SHEET_ID, "Weapons"),
    "units": (SHEET_ID, "Units"),
    "unit_point_brackets": (SHEET_ID, "Unit Point Brackets"),
    "datasheets": (SHEET_ID, "Datasheets"),
    "leadership": (SHEET_ID, "Leaderships"),
}

class Command(BaseCommand):
    help = "Download latest CSVs from Google Sheets"

    def handle(self, *args, **options):
        timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
        version_dir = DATA_DIR / timestamp
        version_dir.mkdir(parents=True, exist_ok=True)
        for name, (sheet_id, tab) in SHEETS.items():
            url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={tab}"
            out_path = version_dir / f"{name}.csv"
            resp = requests.get(url)
            resp.raise_for_status()
            out_path.write_bytes(resp.content)
            self.stdout.write(self.style.SUCCESS(f"Updated {name}.csv"))

