"""
Deduplicator — Detects and merges duplicate notifications across sources.
Uses fuzzy title matching and organization matching to find duplicates.
When duplicates are found, keeps the one with highest confidence and merges
missing fields from the other.
"""

import re
from difflib import SequenceMatcher


def deduplicate(items, similarity_threshold=0.80):
    """
    Remove duplicate notifications from the combined item list.
    
    Algorithm:
    1. Group items by organization (exact match after normalization)
    2. Within each group, compare titles using fuzzy matching
    3. If similarity > threshold, merge the items (keep highest confidence)
    
    Returns: (deduplicated_items, duplicate_count)
    """
    if not items:
        return [], 0

    # Group by normalized organization name
    groups = {}
    for item in items:
        org_key = _normalize_org(item.get("organization", ""))
        groups.setdefault(org_key, []).append(item)

    deduplicated = []
    duplicate_count = 0

    for org_key, group in groups.items():
        merged_group = _deduplicate_group(group, similarity_threshold)
        duplicate_count += len(group) - len(merged_group)
        deduplicated.extend(merged_group)

    # Sort by confidence (highest first), then by date
    deduplicated.sort(
        key=lambda x: (
            x.get("confidence", 0),
            x.get("importantDates", {}).get("notificationDate", "0000"),
        ),
        reverse=True,
    )

    return deduplicated, duplicate_count


def _deduplicate_group(group, threshold):
    """Deduplicate items within a single organization group."""
    if len(group) <= 1:
        return group

    # Track which items have been merged
    merged = [False] * len(group)
    result = []

    for i in range(len(group)):
        if merged[i]:
            continue

        current = group[i]

        for j in range(i + 1, len(group)):
            if merged[j]:
                continue

            similarity = _title_similarity(
                current.get("title", ""),
                group[j].get("title", ""),
            )

            if similarity >= threshold:
                # Merge: keep higher confidence, fill missing fields
                current = _merge_items(current, group[j])
                merged[j] = True

        result.append(current)

    return result


def _title_similarity(title1, title2):
    """Calculate similarity between two notification titles."""
    t1 = _normalize_title(title1)
    t2 = _normalize_title(title2)

    if t1 == t2:
        return 1.0

    return SequenceMatcher(None, t1, t2).ratio()


def _normalize_title(title):
    """Normalize title for comparison."""
    if not title:
        return ""
    title = title.lower().strip()
    # Remove common prefixes/suffixes
    title = re.sub(r"\[.*?\]", "", title)
    title = re.sub(r"\(.*?\)", "", title)
    # Remove years (they vary between sources)
    title = re.sub(r"20\d{2}", "", title)
    # Remove extra whitespace
    title = re.sub(r"\s+", " ", title).strip()
    return title


def _normalize_org(org):
    """Normalize organization name for grouping."""
    if not org:
        return ""
    org = org.lower().strip()
    # Extract abbreviation if present
    match = re.search(r"\(([a-z]+)\)", org)
    if match:
        return match.group(1)
    return org


def _merge_items(primary, secondary):
    """
    Merge two duplicate items. Primary has higher confidence.
    Fill missing fields from secondary.
    """
    # Keep the one with higher confidence as base
    if secondary.get("confidence", 0) > primary.get("confidence", 0):
        primary, secondary = secondary, primary

    # Fill missing fields from secondary
    for key in ["totalVacancies", "ageLimit", "applicationFee"]:
        if not primary.get(key) and secondary.get(key):
            primary[key] = secondary[key]

    # Merge dates
    primary_dates = primary.get("importantDates", {})
    secondary_dates = secondary.get("importantDates", {})
    for date_key, date_val in secondary_dates.items():
        if date_key not in primary_dates or not primary_dates[date_key]:
            primary_dates[date_key] = date_val
    primary["importantDates"] = primary_dates

    # Merge links
    primary_links = primary.get("links", {})
    secondary_links = secondary.get("links", {})
    for link_key, link_val in secondary_links.items():
        if link_key not in primary_links or not primary_links[link_key]:
            primary_links[link_key] = link_val
    primary["links"] = primary_links

    # Merge qualifications
    primary_quals = set(primary.get("qualifications", []))
    secondary_quals = set(secondary.get("qualifications", []))
    primary["qualifications"] = list(primary_quals | secondary_quals)

    # Track that this item was merged from multiple sources
    sources = primary.get("mergedSources", [primary.get("source", "")])
    if secondary.get("source") and secondary["source"] not in sources:
        sources.append(secondary["source"])
    primary["mergedSources"] = sources

    return primary
