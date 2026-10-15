import re

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