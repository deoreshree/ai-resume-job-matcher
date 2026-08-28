"""Text normalization helpers."""

from __future__ import annotations

import re
import unicodedata

_BULLETS = str.maketrans(
    {
        "\u2022": "-",
        "\u2023": "-",
        "\u2043": "-",
        "\u2219": "-",
        "\u25E6": "-",
        "\u25AA": "-",
        "\u25AB": "-",
        "\u25CF": "-",
        "\u25CB": "-",
        "\uf0b7": "-",
        "\uf0a7": "-",
        "•": "-",
        "●": "-",
        "○": "-",
        "▪": "-",
        "‣": "-",
    }
)

_MULTI_SPACE = re.compile(r"[^\S\n]+")
_MULTI_NEWLINE = re.compile(r"\n{3,}")
_SOFT_HYPHEN = "\u00ad"


def clean_text(text: str) -> str:
    """Normalize whitespace, bullets, and encoding artifacts."""
    if not text:
        return ""

    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\x00", " ").replace(_SOFT_HYPHEN, "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.translate(_BULLETS)
    text = text.replace("\u00a0", " ")
    text = _MULTI_SPACE.sub(" ", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    text = _MULTI_NEWLINE.sub("\n\n", text)
    return text.strip()
