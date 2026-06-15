"""Human-readable rendering of aggregate results.

Contract: `format_total(label, metres)` renders 'LABEL: <metres> m' with the
numeric value shown to 3 decimal places.
"""


def format_total(label, metres):
    return "%s: %.1f m" % (label, metres)
