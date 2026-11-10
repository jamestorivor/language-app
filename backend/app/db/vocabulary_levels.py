"""Bundled approximate proficiency levels for dictionary entries."""
import csv
from functools import lru_cache
from pathlib import Path
import unicodedata

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def normalize_english(word: str) -> str:
    return unicodedata.normalize("NFKC", word).casefold().replace("’", "'")


@lru_cache(maxsize=1)
def japanese_levels() -> dict[int, str]:
    with (DATA_DIR / "jlpt_levels.csv").open(encoding="utf-8", newline="") as source:
        return {int(row["source_entry_id"]): row["level"] for row in csv.DictReader(source)}


@lru_cache(maxsize=1)
def english_levels() -> dict[str, str]:
    levels: dict[str, str] = {}
    order = ("A1", "A2", "B1", "B2", "C1", "C2")
    with (DATA_DIR / "cefr_levels.csv").open(encoding="utf-8", newline="") as source:
        for row in csv.DictReader(source):
            key = normalize_english(row["headword"])
            level = row["level"]
            if key not in levels or order.index(level) < order.index(levels[key]):
                levels[key] = level
    return levels
