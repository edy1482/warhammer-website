from django.core.files.storage import storages


def scraped_html_storage():
    """
    Storage backend for raw scraped HTML.

    Passed to the FileField as a callable so the backend is looked up from
    settings.STORAGES["scraped_html"] at runtime: S3 when AWS settings are
    present, local disk otherwise. Because it's a callable, migrations record
    the function path instead of baking a specific backend into the schema.
    """
    return storages["scraped_html"]
