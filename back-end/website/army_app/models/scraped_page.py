from django.db import models
from django.core.exceptions import ValidationError

MAX_CHARFIELD_LENGTH = 255

class ScrapedPage(models.Model):
    """
    Stores the raw HTML (and basic metadata) of a scraped datasheet webpage.
    """

    STATUS_PENDING = "pending"
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_SUCCESS, "Success"),
        (STATUS_FAILED, "Failed"),
    ]

    FACTION_CLUSTER = "faction cluster"
    UNIT_CLUSTER = "unit cluster"
    UNKNOWN_CLUSTER = "unknown cluster"

    PAGE_CHOICES = [
        (FACTION_CLUSTER, "Faction Cluster"),
        (UNIT_CLUSTER, "Unit Cluster"),
        (UNKNOWN_CLUSTER, "Unknown Cluster"),
    ]

    url = models.URLField(max_length = 1000, unique=True)
    html_content = models.TextField(blank = True, null=True)
    file_path = models.CharField(max_length = 500, blank=True, null=True)
    status_code = models.IntegerField(blank = True, null=True)
    status = models.CharField(max_length = MAX_CHARFIELD_LENGTH, choices = STATUS_CHOICES, default = STATUS_PENDING)
    page_type = models.CharField(max_length = MAX_CHARFIELD_LENGTH, choices = PAGE_CHOICES, default = UNIT_CLUSTER)
    error_message = models.TextField(blank = True, null = True)
    scraped_at = models.DateTimeField(blank = True, null = True)
    created_at = models.DateTimeField(auto_now_add = True)
    updated_at = models.DateTimeField(auto_now = True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.url} ({self.status})"

class ScrapedPageLoadResult(models.Model):
    """
    Stores the result of turning the scraped page into model objects
    """
    STATUS_UNLOADED = "unloaded"
    STATUS_LOADED = "loaded"
    STATUS_FAILED = "load_failed"
    
    STATUS_CHOICES = [
        (STATUS_UNLOADED, "Unloaded"),
        (STATUS_LOADED, "Loaded"),
        (STATUS_FAILED, "Load Failed"),
    ]

    TARGET_MODEL_CHOICES = [
        ("Faction", "Faction"),
        ("Detachment", "Detachment"),
        ("Stratagem", "Stratagem"),
        ("Enhancement", "Enhancement"),
        ("Unit", "Unit"),
        ("UnitPointBracket", "Unit Point Bracket"),
        ("Leadership", "Leadership"),
        ("Ability", "Ability"),
        ("AbilityEffect", "Ability Effect"),
        ("Phase", "Phase"),
        ("KeyWord", "Keyword"),
    ]

    page = models.ForeignKey(ScrapedPage, on_delete=models.CASCADE, help_text="The result of processing a scraped page", related_name="load_results")
    target_model = models.CharField(max_length=MAX_CHARFIELD_LENGTH, choices=TARGET_MODEL_CHOICES)
    # Identifies the specific item within the page: unit anchor slug
    # ("Custodian-Guard"), stratagem name, detachment name, etc.
    source_key = models.CharField(max_length=MAX_CHARFIELD_LENGTH)
    
    status = models.CharField(max_length = MAX_CHARFIELD_LENGTH, choices = STATUS_CHOICES, default = STATUS_UNLOADED)
    error_msg = models.TextField(blank = True, null = True)
    
    loaded_at = models.DateTimeField(blank = True, null = True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["page", "target_model", "source_key"],
                name="unique_load_result_per_item",
            ),
        ]
        indexes = [
            models.Index(fields=["target_model", "status"]),
        ]
        ordering = [
            "page",
            "target_model",
            "source_key",
        ]

    def __str__(self):
        return f"{self.target_model}:{self.source_key} ({self.status})"