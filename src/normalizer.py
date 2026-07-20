"""
Normalizer — Converts raw scraped data into the unified JSON schema.
Also validates and cleans data before writing to output files.
"""

import re
from datetime import datetime, timezone


# The unified schema all scraped items must conform to
REQUIRED_FIELDS = ["id", "title", "organization", "source", "status"]


def normalize_item(item):
    """
    Normalize a single scraped item to the unified output schema.
    Fills in defaults, cleans data, and validates required fields.
    """
    # Ensure required fields exist
    for field in REQUIRED_FIELDS:
        if field not in item or not item[field]:
            return None  # Skip invalid items

    # Clean title
    item["title"] = _clean_title(item["title"])
    if not item["title"] or len(item["title"]) < 5:
        return None

    # Ensure standard fields have defaults
    item.setdefault("organizationShort", _abbreviate(item["organization"]))
    item.setdefault("category", "central")
    item.setdefault("subcategory", "general")
    item.setdefault("notificationType", "notification")
    item.setdefault("totalVacancies", None)
    item.setdefault("qualifications", [])
    item.setdefault("ageLimit", None)
    item.setdefault("importantDates", {})
    item.setdefault("applicationFee", None)
    item.setdefault("links", {})
    item.setdefault("sourceType", "html")
    item.setdefault("confidence", 0.70)
    item.setdefault("status", "active")

    # Add metadata
    item["lastUpdated"] = datetime.now(timezone.utc).isoformat()

    # Remove internal/raw fields not needed in output
    item.pop("rawData", None)

    return item


def normalize_batch(items):
    """Normalize a batch of items, filtering out invalid ones."""
    normalized = []
    skipped = 0

    for item in items:
        result = normalize_item(item)
        if result:
            normalized.append(result)
        else:
            skipped += 1

    return normalized, skipped


def _clean_title(title):
    """Clean up a notification title."""
    if not title:
        return ""
    # Remove excessive whitespace
    title = re.sub(r"\s+", " ", title).strip()
    # Remove common junk prefixes
    title = re.sub(r"^(new!?\s*|hot!?\s*|latest!?\s*|\*+\s*)", "", title, flags=re.IGNORECASE)
    # Remove HTML entities
    title = title.replace("&amp;", "&").replace("&nbsp;", " ").replace("&#8211;", "–")
    return title.strip()


def _abbreviate(org_name):
    """Generate abbreviation from organization name."""
    if not org_name:
        return ""
    # Extract uppercase words or words in parentheses
    paren = re.search(r"\(([A-Z]{2,})\)", org_name)
    if paren:
        return paren.group(1)
    # Take first letter of each major word
    words = [w for w in org_name.split() if len(w) > 2 and w[0].isupper()]
    return "".join(w[0] for w in words[:5])
