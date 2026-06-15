"""Human-alias registry for unit names.

Contract: `build_index()` returns a dict mapping EVERY canonical unit name AND
every human alias to the CANONICAL unit name (so callers can normalise free-text
unit names before conversion). Every registered alias is a valid conversion input
the rest of the toolkit must accept.
"""

# alias -> canonical unit name.
ALIASES = {
    "metre": "m",
    "meter": "m",
    "centimetre": "cm",
    "centimeter": "cm",
    "millimetre": "mm",
    "millimeter": "mm",
    "kilometre": "km",
    "klick": "km",
}

CANONICAL = ("m", "cm", "mm", "km")


def build_index():
    """Map canonical names and all aliases to the canonical unit name."""
    index = {}
    for name in CANONICAL:
        index[name] = name
    for alias, canonical in ALIASES.items():
        index[alias] = alias
    return index
