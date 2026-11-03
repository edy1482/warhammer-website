import hashlib
from urllib.parse import urlparse

import army_app.storage
from django.core.files.base import ContentFile
from django.db import migrations, models


def _filename_for(url):
    # Same scheme as web_scraper._build_filename, frozen here so later
    # changes to the command can't alter what this migration does.
    parsed = urlparse(url)
    slug = (parsed.netloc + parsed.path).strip("/").replace("/", "_") or "page"
    url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()[:10]
    return f"{slug[:150]}_{url_hash}.html"


def copy_html_into_storage(apps, schema_editor):
    """Move html_content from the DB column into the file storage (S3 in prod)."""
    ScrapedPage = apps.get_model("army_app", "ScrapedPage")
    pages = ScrapedPage.objects.exclude(html_content__isnull=True).exclude(html_content="")
    for page in pages.iterator():
        page.html_file.save(
            _filename_for(page.url),
            ContentFile(page.html_content.encode("utf-8")),
            save=False,
        )
        page.save(update_fields=["html_file"])


def copy_html_back_to_db(apps, schema_editor):
    ScrapedPage = apps.get_model("army_app", "ScrapedPage")
    for page in ScrapedPage.objects.exclude(html_file="").exclude(html_file__isnull=True).iterator():
        with page.html_file.open("rb") as f:
            page.html_content = f.read().decode("utf-8")
        page.file_path = page.html_file.name
        page.save(update_fields=["html_content", "file_path"])


class Migration(migrations.Migration):

    dependencies = [
        ("army_app", "0030_merge_20261103_1051"),
    ]

    operations = [
        migrations.AddField(
            model_name="scrapedpage",
            name="html_file",
            field=models.FileField(
                blank=True,
                max_length=500,
                null=True,
                storage=army_app.storage.scraped_html_storage,
                upload_to="",
            ),
        ),
        migrations.RunPython(copy_html_into_storage, copy_html_back_to_db),
        migrations.RemoveField(
            model_name="scrapedpage",
            name="html_content",
        ),
        migrations.RemoveField(
            model_name="scrapedpage",
            name="file_path",
        ),
    ]
