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

# Test some urls out
URLS = [
    "https://wahapedia.ru/wh40k11ed/factions/necrons/Immortals",
    "https://wahapedia.ru/wh40k11ed/factions/necrons/Necron-Warriors",
    "https://wahapedia.ru/wh40k11ed/factions/necrons/Skorpekh-Destroyers",
]

REQUEST_TIMEOUT = 15  # seconds
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; DatasheetScraperBot/1.0; "
        "+https://example.com/bot)"
    )
}

BASE_DIR = Path(__file__).resolve().parents[2]
HTML_DIR = BASE_DIR / "data" / "html"


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

        # Let's slim down the html by removing script tags
        soup = BeautifulSoup(html, "html.parser")

        for tag in soup.find_all("script"):
            tag.decompose()

        for tag in soup.find_all("link"):
            tag.decompose()

        for tag in soup.find_all("meta"):
            tag.decompose()

        soup_string = str(soup)
        soup_string = "".join([s for s in soup_string.strip().splitlines(True) if s.strip()])

        with open(full_path, "w", encoding="utf-8") as f:
            f.write(soup_string)

        # Store a path relative to MEDIA_ROOT on the model.
        return soup_string, os.path.join("datasheets", "html", filename)