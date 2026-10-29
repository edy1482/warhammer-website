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