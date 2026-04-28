from __future__ import annotations

import pykakasi

_kks = pykakasi.kakasi()


def to_reading(text: str) -> str:
    """Convert text to hiragana reading for normalization."""
    result = _kks.convert(text)
    parts = []
    for item in result:
        hira = item.get("hira", "")
        parts.append(hira if hira else item.get("orig", ""))
    return "".join(parts)
