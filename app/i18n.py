"""Chargement des dictionnaires de traduction et résolution de la langue active."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

I18N_DIR = Path(__file__).parent / "i18n"
SUPPORTED_LANGUAGES = ("fr", "en")

_translations: dict[str, dict[str, str]] = {}


def load_translations() -> None:
    for lang in SUPPORTED_LANGUAGES:
        with open(I18N_DIR / f"{lang}.json", encoding="utf-8") as f:
            _translations[lang] = json.load(f)


def get_translator(language: str) -> Callable[[str], str]:
    """Retourne une fonction t(key) résolvant la clé dans la langue donnée."""
    if not _translations:
        load_translations()
    table = _translations.get(language, _translations["fr"])
    fallback = _translations["fr"]

    def t(key: str) -> str:
        return table.get(key, fallback.get(key, key))

    return t
