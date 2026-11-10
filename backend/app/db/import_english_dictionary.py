"""Import EJDict's UTF-8 tab-separated source, preserving its Japanese notation."""
import argparse
from collections import defaultdict
from pathlib import Path
import unicodedata
from zipfile import ZipFile

from sqlalchemy import select

from app.db.models.english_vocab import EnglishDictionary
from app.db.session import SessionLocal

DEFAULT_SOURCE = Path(__file__).resolve().parents[3] / "data" / "EJDict.zip"
BATCH_SIZE = 500


def lookup_key(word: str) -> str:
    return unicodedata.normalize("NFKC", word).casefold().replace("’", "'")


def read_entries(path: Path) -> dict[str, str]:
    entries: dict[str, list[str]] = defaultdict(list)

    def read_lines(lines, name: str) -> None:
        for number, raw_line in enumerate(lines, 1):
            line = raw_line.rstrip("\r\n")
            if not line.strip():
                continue
            if "\t" not in line:
                raise ValueError(f"{name}:{number}: expected a tab-separated headword and meaning")
            headwords, meaning = line.split("\t", 1)
            meaning = meaning.strip()
            variants = [word.strip() for word in headwords.split(",")]
            if not meaning or not all(variants):
                raise ValueError(f"{name}:{number}: empty headword or meaning")
            for word in variants:
                if meaning not in entries[word]:
                    entries[word].append(meaning)

    if path.suffix.lower() == ".zip":
        with ZipFile(path) as archive:
            names = sorted(name for name in archive.namelist() if "/src/" in name and name.endswith(".txt"))
            if not names:
                raise ValueError("ZIP must contain EJDict src/*.txt files")
            for name in names:
                read_lines(archive.read(name).decode("utf-8-sig").splitlines(), name)
    else:
        with path.open(encoding="utf-8-sig") as source:
            read_lines(source, str(path))
    if not entries:
        raise ValueError("Dictionary source contains no entries")
    return {word: "\n".join(meanings) for word, meanings in entries.items()}


def import_entries(session, entries: dict[str, str]) -> tuple[int, int]:
    """Insert/update without changing IDs or deleting entries with saved progress."""
    added = updated = 0
    words = list(entries)
    for start in range(0, len(words), BATCH_SIZE):
        batch = words[start:start + BATCH_SIZE]
        existing = {entry.headword: entry for entry in session.scalars(
            select(EnglishDictionary).where(EnglishDictionary.headword.in_(batch))
        )}
        for word in batch:
            meaning = entries[word]
            key = lookup_key(word)
            entry = existing.get(word)
            if entry is None:
                session.add(EnglishDictionary(headword=word, lookup_key=key, meaning=meaning))
                added += 1
            elif entry.meaning != meaning or entry.lookup_key != key:
                entry.meaning = meaning
                entry.lookup_key = key
                updated += 1
        session.flush()
    return added, updated


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", nargs="?", type=Path, default=DEFAULT_SOURCE,
                        help="EJDict source ZIP or UTF-8 tab-separated file")
    args = parser.parse_args()
    entries = read_entries(args.source)
    with SessionLocal.begin() as session:
        added, updated = import_entries(session, entries)
    print(f"Imported {len(entries)} headwords: {added} added, {updated} updated.")


if __name__ == "__main__":
    main()
