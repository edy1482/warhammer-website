import re
from collections import Counter

from army_app.models import Ability

# Base names that take a value. Extend this when a new one turns up.
_PARAMETERISED = re.compile(
    r"^(?P<base>sustained hits|rapid fire|melta|feel no pain|scouts|deadly demise|firing deck|anti-[\w-]+)"
    r"\s+(?P<value>\S.*)$",
    re.IGNORECASE,
)

def split_ability(text):
    text = text.strip()
    m = _PARAMETERISED.match(text)
    if not m:
        return text, ""
    return m["base"].title(), m["value"].strip()

def resolve_ability(text):
    base, value = split_ability(text)
    return Ability.objects.get(name=base, value=value)

# Standardize the unique weapon name
def weapon_name(base, unit, weapon_type):
    return f"{base} ({unit, weapon_type})"
 
_QUOTES = str.maketrans({
    "‘": "'", "’": "'",   # curly single quotes
    "“": '"', "”": '"',   # curly double quotes
})

def normalise(text):
    """Straighten quotes and collapse whitespace."""
    return " ".join(str(text).translate(_QUOTES).split())

def display_name(base):
    return normalise(base)
 
def weapon_name(base, unit, weapon_type):
    return f"{normalise(base)} ({normalise(unit)}, {normalise(weapon_type).lower()})"

def assert_unique(names):
    """
    Call on every weapon name a scrape produces, before loading.
    Two profiles with the same (base, unit, type) would otherwise be
    silently merged by update_or_create, with the last one winning.
    """
    dupes = sorted(n for n, c in Counter(names).items() if c > 1)
    if dupes:
        raise ValueError(f"Duplicate weapon names produced: {dupes}")

"""
Collapse rows that describe the same thing under several parents.
 
wahapedia lists a shared stratagem/enhancement once per detachment. The model
holds it once, linked to all of them. This merges those rows and REFUSES to
merge if the copies disagree, so two different entries that merely share a
name can never be silently collapsed into one.
 
    merge_duplicates(
        rows,
        key="name",
        union_field="detachments",              # semicolon-joined, unioned
        same_fields=("when", "target", "effect", "restrictions", "cost"),
        label="Stratagem",
    )
"""

def _norm(value):
    return " ".join(str(value).split())

def _split(cell):
    return [p.strip() for p in str(cell or "").split(";") if p.strip()]

def merge_duplicates(rows, key, union_field, same_fields, label):
    merged, conflicts = {}, []
 
    for row in rows:
        k = _norm(row[key])
        if k not in merged:
            merged[k] = dict(row)
            merged[k][union_field] = _split(row[union_field])
            continue
 
        first = merged[k]
        for field in same_fields:
            if _norm(first[field]) != _norm(row[field]):
                conflicts.append(
                    f"{label} '{k}': field '{field}' differs between copies "
                    f"({_norm(first[field])[:60]!r} vs {_norm(row[field])[:60]!r})"
                )
        for name in _split(row[union_field]):
            if name not in first[union_field]:
                first[union_field].append(name)
 
    if conflicts:
        raise ValueError("Same name, different content - not merging:\n  " + "\n  ".join(conflicts))
 
    out = []
    for row in merged.values():
        row[union_field] = ";".join(sorted(row[union_field]))
        out.append(row)
    return out