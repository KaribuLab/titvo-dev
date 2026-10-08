"""Titvo's indigo brand palette shared by terminal panels and prompts."""

from rich.theme import Theme

PRIMARY = "#4f46e5"
ACCENT = "#818cf8"
SOFT = "#c7d2fe"
BORDER = "#48465c"
THEME = Theme(
    {
        "brand": ACCENT,
        "brand.title": f"bold {SOFT}",
        "brand.border": BORDER,
        "cyan": ACCENT,
    }
)
