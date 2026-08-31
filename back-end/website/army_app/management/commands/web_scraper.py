import requests
import os
import logging
import hashlib
from datetime import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from pathlib import Path
from army_app.models.core import ScrapedPage
from urllib.parse import urlparse
from bs4 import BeautifulSoup

# Prefixes
NECRON = "https://wahapedia.ru/wh40k11ed/factions/necrons/"
ORK = "https://wahapedia.ru/wh40k11ed/factions/orks/"
CUSTODES = "https://wahapedia.ru/wh40k11ed/factions/adeptus-custodes/"
TYRANIDS = "https://wahapedia.ru/wh40k11ed/factions/tyranids/"
# This grabs all SPM Chapters - maybe make exception for this faction?
SPACE_MARINE = "https://wahapedia.ru/wh40k11ed/factions/space-marines/"
AELDARI = "https://wahapedia.ru/wh40k11ed/factions/aeldari/"
DRUKHARI = "https://wahapedia.ru/wh40k11ed/factions/drukhari/"
TAU = "https://wahapedia.ru/wh40k11ed/factions/t-au-empire/"
GENESTEALER = "https://wahapedia.ru/wh40k11ed/factions/genestealer-cults/"
LEAGUES = "https://wahapedia.ru/wh40k11ed/factions/leagues-of-votann/"
SORORITAS = "https://wahapedia.ru/wh40k11ed/factions/adepta-sororitas/"
MECHANICUS = "https://wahapedia.ru/wh40k11ed/factions/adeptus-mechanicus/"
ASTRA_MIL = "https://wahapedia.ru/wh40k11ed/factions/astra-militarum/"
GREY_KNIGHTS = "https://wahapedia.ru/wh40k11ed/factions/grey-knights/"
IMP_AGENTS = "https://wahapedia.ru/wh40k11ed/factions/imperial-agents/"
# IMP Knights can take certain AD_MECH units in a detachment (new datasheets as Faction Ability is removed)
# IMPERIUM Factions can take IMP_KNIGHTS as allies
IMP_KNIGHTS = "https://wahapedia.ru/wh40k11ed/factions/imperial-knights/"
# Chaos Daemons can take certain Chaos SPM units in a detachment (Duplicates - they get their Faction Ability)
# Chaos Daemons can be taken as allies for Chaos SPM or Chaos Knights - allies rule
CHAOS_DAEM = "https://wahapedia.ru/wh40k11ed/factions/chaos-daemons/"
# Chaos Knights can take certain Chaos SPM units in a detachment (remove faction ability - new datasheets)
CHAOS_KNIGHTS = "https://wahapedia.ru/wh40k11ed/factions/chaos-knights/"
# Chaos SPM can take the 4 Chaos sub-faction marines (new datasheets - faction ability replaced with Dark Pacts)
CHAOS_SPM = "https://wahapedia.ru/wh40k11ed/factions/chaos-space-marines/"
# Death Guard can take certain Chaos Daemons (new datasheet, as keywords changed)
DEATH = "https://wahapedia.ru/wh40k11ed/factions/death-guard/"
# Emperor's Children can take certain Chaos Daemons (new datasheet, as keywords changed)
EMP_CHILD = "https://wahapedia.ru/wh40k11ed/factions/emperor-s-children/"
# Thousand Sons can take certain Chaos Daemons (new datasheet, as keywords changed)
THOU_SONS = "https://wahapedia.ru/wh40k11ed/factions/thousand-sons/"
# World Eaters can take certain Chaos Daemons (new datasheet, as keywords changed)
WORLD_EAT = "https://wahapedia.ru/wh40k11ed/factions/world-eaters/"

SUFFIX = "datasheets.html"

REQUEST_TIMEOUT = 15  # seconds
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; DatasheetScraperBot/1.0; "
        "+https://example.com/bot)"
    )
}

PREFIXES = [
    SORORITAS,
    CUSTODES,
    ASTRA_MIL,
    GREY_KNIGHTS,
    IMP_AGENTS,
    IMP_KNIGHTS,
    SPACE_MARINE,
    CHAOS_DAEM,
    CHAOS_KNIGHTS,
    CHAOS_SPM,
    DEATH,
    EMP_CHILD,
    THOU_SONS,
    WORLD_EAT,
    AELDARI,
    DRUKHARI,
    GENESTEALER,
    LEAGUES,
    NECRON,
    ORK,
    TAU,
    TYRANIDS,
]

BASE_DIR = Path(__file__).resolve().parents[2]
HTML_DIR = BASE_DIR / "html_data"


class Command(BaseCommand):
    help = "Download webpages for processing."

    def add_arguments(self, parser):
        parser.add_argument(
            "--urls",
            nargs="*",
            default=None,
            help="Optional list of URLs to scrape instead of the URLS constant.",
        )

    def handle(self, *args, **options):
        # Create the URL list
        URLS = [url + SUFFIX for url in PREFIXES]

        # Grab logger
        logger = logging.getLogger("web_scraper")
        logger.setLevel(logging.INFO)
        # Write logger intro
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info("=" * 80)
        logger.info(f"Starting web page downloads at {timestamp}")
        logger.info("=" * 80)

        urls = options.get("urls") or URLS

        if not urls:
            logger.warning("No URLs provided. Fill in the URLS list in scrape_datasheets.py or pass --urls.")
            return

        output_dir = HTML_DIR
        output_dir.mkdir(parents=True, exist_ok=True)

        for url in urls:
            logger.info(f"Scraping: {url}")
            page, _ = ScrapedPage.objects.get_or_create(url=url)

            try:
                response = requests.get(
                    url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT
                )
                response.raise_for_status()

                html = response.text
                html, file_path = self._save_html_to_disk(url, html, output_dir)

                page.html_content = html
                page.file_path = file_path
                page.status_code = response.status_code
                page.status = ScrapedPage.STATUS_SUCCESS
                page.error_message = None
                page.scraped_at = timezone.now()
                page.save()

                logger.info(f"  Saved -> {file_path}")

            except requests.RequestException as exc:
                page.status = ScrapedPage.STATUS_FAILED
                page.error_message = str(exc)
                page.status_code = getattr(exc.response, "status_code", None)
                page.scraped_at = timezone.now()
                page.save()

                logger.error(f"  Failed: {exc}")

        # Write logger outro
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info("=" * 80)
        logger.info(f"Finished web_page downloads at {timestamp}")
        logger.info("=" * 80)
        return

    def _save_html_to_disk(self, url, html, output_dir):
        """
        Build a filesystem-safe filename from the URL and write the HTML
        to army_app/data/html/<filename>.html
        """
        parsed = urlparse(url)
        slug = (parsed.netloc + parsed.path).strip("/").replace("/", "_")
        if not slug:
            slug = "page"

        # Keep filenames from getting too long / avoid collisions on
        # near-identical slugs by appending a short hash of the full URL.
        url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()[:10]
        filename = f"{slug[:150]}_{url_hash}.html"
        full_path = os.path.join(output_dir, filename)

        # Let's slim down the html by finding the relevant info
        soup = BeautifulSoup(html, "html.parser")

        soup_str = str(soup.find_all("div", "dsOuterFrame datasheet pagebreak clFl"))

        with open(full_path, "w", encoding="utf-8") as f:
            f.write(soup_str)

        # Store a path relative to html_data on the model.
        return soup_str, os.path.join("html_data", filename)