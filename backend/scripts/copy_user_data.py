"""Preview or replace one user's data with another user's data.

Run from backend with DATABASE_URL explicitly set.  The default is read-only;
--apply performs the replacement in one transaction.  See --help.
"""
import argparse
import hashlib
import json
import os
import sys

from sqlalchemy import MetaData, Table, create_engine, delete, func, inspect, select, text, update


OWNED = (
    "podcasts", "podcast_chunk", "podcast_vocabulary_baseline",
    "user_japanese_word_progress", "user_english_word_progress",
    "study_cards", "sentence_study_familiarity", "sentence_study_memberships",
    "sentence_study_schedules", "sentence_study_occurrences", "sentence_study_review_logs",
    "english_study_cards", "english_sentence_study_familiarity", "english_sentence_study_memberships",
    "english_sentence_study_schedules", "english_sentence_study_occurrences", "english_sentence_study_review_logs",
)
LEGACY = (
    "vocabulary_study_memberships", "vocabulary_study_schedules", "vocabulary_occurrences",
    "vocabulary_study_review_logs", "legacy_sentence_card_archive",
)
CHILDREN = ("podcast_transcript", "podcast_vocabulary_analysis", "study_reviews")
TABLES = ("users", "alembic_version", *OWNED, *LEGACY, *CHILDREN)


def rows(conn, table, condition):
    return [dict(row) for row in conn.execute(select(table).where(condition)).mappings()]


def copy_json_card(value, old_id, new_id):
    if isinstance(value, dict):
        return {k: (new_id if k == "card_id" and v == old_id else copy_json_card(v, old_id, new_id)) for k, v in value.items()}
    if isinstance(value, list):
        return [copy_json_card(v, old_id, new_id) for v in value]
    return value


def insert_with_id(conn, table, data):
    return conn.execute(table.insert().values(**data).returning(table.c.id)).scalar_one()


def remap_id(mapping, value, field):
    if value is None:
        return None
    if value not in mapping:
        raise ValueError(f"Source {field} references a record outside the source account")
    return mapping[value]


def run(conn, source, destination, expected_clerk_id, apply):
    if source == destination:
        raise ValueError("Source and destination must be different users")
    if conn.dialect.name != "postgresql":
        raise ValueError("This script supports PostgreSQL only")
    metadata = MetaData()
    tables = {name: Table(name, metadata, autoload_with=conn) for name in TABLES}
    if conn.execute(select(tables["alembic_version"].c.version_num)).scalars().all() != ["e2f3a4b5c6d7"]:
        raise ValueError("Database schema does not match revision e2f3a4b5c6d7")

    # Prevent either account's data changing between the snapshot and commit.
    if apply:
        names = ", ".join('"' + name + '"' for name in sorted(set(TABLES) - {"alembic_version"}))
        conn.execute(text(f"LOCK TABLE {names} IN SHARE ROW EXCLUSIVE MODE"))

    users = tables["users"]
    source_user = conn.execute(select(users).where(users.c.id == source)).mappings().one_or_none()
    dest_user = conn.execute(select(users).where(users.c.id == destination)).mappings().one_or_none()
    if source_user is None or dest_user is None:
        raise ValueError("Both user IDs must exist")
    if source_user["name"] != "test_user":
        raise ValueError("Source user is not named test_user; check the IDs")
    if dest_user["clerk_id"] != expected_clerk_id:
        raise ValueError("Destination Clerk ID does not match; check the database and IDs")

    inspector = inspect(conn)
    for name in inspector.get_table_names():
        if name not in TABLES and any(col["name"] == "user_id" for col in inspector.get_columns(name)):
            raise ValueError(f"Unrecognized user-owned table {name}; a tailored migration is required")

    # Older migration snapshots have special provenance and cannot safely be
    # duplicated by this script. Refuse rather than omit or destroy them.
    for name in LEGACY:
        t = tables[name]
        count = conn.scalar(select(func.count()).select_from(t).where(t.c.user_id.in_([source, destination])))
        if count:
            raise ValueError(f"{name} contains legacy data for one of the users; a tailored migration is required")

    data = {name: rows(conn, tables[name], tables[name].c.user_id == source) for name in OWNED}
    for name in OWNED:
        t = tables[name]
        dest_count = conn.scalar(select(func.count()).select_from(t).where(t.c.user_id == destination))
        print(f"{name}: source {len(data[name])}, destination {dest_count}")
    if not apply:
        print("Preview only; no data changed.")
        return

    # Capture records without user_id before deleting any destination data.
    source_chunk_ids = [r["id"] for r in data["podcast_chunk"]]
    source_card_ids = [r["id"] for r in data["study_cards"]]
    transcripts = rows(conn, tables["podcast_transcript"], tables["podcast_transcript"].c.podcast_chunk_id.in_(source_chunk_ids))
    analyses = rows(conn, tables["podcast_vocabulary_analysis"], tables["podcast_vocabulary_analysis"].c.chunk_id.in_(source_chunk_ids))
    reviews = rows(conn, tables["study_reviews"], tables["study_reviews"].c.card_id.in_(source_card_ids))

    # Remove children before parents. No source account rows are deleted.
    for prefix in ("english_", ""):
        for suffix in ("sentence_study_review_logs", "sentence_study_schedules", "sentence_study_memberships", "sentence_study_occurrences", "sentence_study_familiarity"):
            t = tables[prefix + suffix]
            conn.execute(delete(t).where(t.c.user_id == destination))
    dest_cards = select(tables["study_cards"].c.id).where(tables["study_cards"].c.user_id == destination)
    conn.execute(delete(tables["study_reviews"]).where(tables["study_reviews"].c.card_id.in_(dest_cards)))
    for name in ("study_cards", "english_study_cards", "user_japanese_word_progress", "user_english_word_progress", "podcast_vocabulary_baseline"):
        t = tables[name]
        conn.execute(delete(t).where(t.c.user_id == destination))
    dest_chunks = select(tables["podcast_chunk"].c.id).where(tables["podcast_chunk"].c.user_id == destination)
    conn.execute(delete(tables["podcast_transcript"]).where(tables["podcast_transcript"].c.podcast_chunk_id.in_(dest_chunks)))
    conn.execute(delete(tables["podcast_vocabulary_analysis"]).where(tables["podcast_vocabulary_analysis"].c.chunk_id.in_(dest_chunks)))
    for name in ("podcast_chunk", "podcasts"):
        t = tables[name]
        conn.execute(delete(t).where(t.c.user_id == destination))

    settings = ("fsrs_retention_percent", "fsrs_maximum_interval", "fsrs_fuzzing", "study_shortcuts")
    conn.execute(update(users).where(users.c.id == destination).values(**{k: source_user[k] for k in settings}))

    episode_map, chunk_map = {}, {}
    for row in data["podcasts"]:
        old = row.pop("id"); row["user_id"] = destination
        episode_map[old] = insert_with_id(conn, tables["podcasts"], row)
    for row in data["podcast_chunk"]:
        old = row.pop("id"); row["user_id"] = destination
        row["podcast_id"] = remap_id(episode_map, row["podcast_id"], "podcast_id")
        chunk_map[old] = insert_with_id(conn, tables["podcast_chunk"], row)
    for row in transcripts:
        row.pop("id"); row["podcast_chunk_id"] = remap_id(chunk_map, row["podcast_chunk_id"], "transcript chunk")
        conn.execute(tables["podcast_transcript"].insert().values(**row))
    for row in analyses:
        row["chunk_id"] = remap_id(chunk_map, row["chunk_id"], "analysis chunk")
        conn.execute(tables["podcast_vocabulary_analysis"].insert().values(**row))
    for row in data["podcast_vocabulary_baseline"]:
        row["user_id"] = destination; row["episode_id"] = remap_id(episode_map, row["episode_id"], "baseline episode")
        conn.execute(tables["podcast_vocabulary_baseline"].insert().values(**row))
    for name in ("user_japanese_word_progress", "user_english_word_progress", "sentence_study_familiarity", "english_sentence_study_familiarity"):
        values = [dict(row, user_id=destination) for row in data[name]]
        if values:
            conn.execute(tables[name].insert(), values)

    for prefix in ("", "english_"):
        card_name = prefix + "study_cards"
        card_map = {}
        for row in data[card_name]:
            old = row.pop("id"); row["user_id"] = destination
            row["episode_id"] = remap_id(episode_map, row["episode_id"], "card episode")
            row["segment_id"] = remap_id(chunk_map, row["segment_id"], "card segment")
            if row["segment_id"] is not None:
                key = json.dumps([row["segment_id"], row["word_id"], row["sentence_start"], row["sentence_end"], row["sentence"]], ensure_ascii=False)
                row["occurrence_key"] = hashlib.sha256(key.encode("utf-8")).hexdigest()
            # Allocate the new ID first; the serialized FSRS card stores it too.
            new = insert_with_id(conn, tables[card_name], row)
            card_map[old] = new
            conn.execute(update(tables[card_name]).where(tables[card_name].c.id == new).values(fsrs_card=copy_json_card(row["fsrs_card"], old, new)))
        for suffix in ("sentence_study_memberships", "sentence_study_schedules", "sentence_study_occurrences", "sentence_study_review_logs"):
            name = prefix + suffix
            for row in data[name]:
                old = row["card_id"]; new = remap_id(card_map, old, "study card")
                row["card_id"] = new; row["user_id"] = destination
                if "id" in row:
                    row.pop("id")
                for key in ("serialized_state", "review_log", "before_state", "after_state"):
                    if key in row:
                        row[key] = copy_json_card(row[key], old, new)
                if "legacy_card_id" in row:
                    row["legacy_card_id"] = remap_id(card_map, row["legacy_card_id"], "legacy card")
                if "legacy_review_id" in row:
                    row["legacy_review_id"] = None
                if "legacy_shared_review_id" in row:
                    row["legacy_shared_review_id"] = None
                if "episode_id" in row:
                    row["episode_id"] = remap_id(episode_map, row["episode_id"], "occurrence episode")
                    row["episode_owner_id"] = destination if row["episode_id"] is not None else None
                    row["segment_id"] = remap_id(chunk_map, row["segment_id"], "occurrence segment")
                    row["segment_episode_id"] = remap_id(episode_map, row["segment_episode_id"], "segment episode")
                    row["segment_owner_id"] = destination if row["segment_id"] is not None else None
                conn.execute(tables[name].insert().values(**row))
        if not prefix:
            for row in reviews:
                old = row["card_id"]; new = remap_id(card_map, old, "review card")
                row.pop("id"); row["card_id"] = new
                for key in ("review_log", "before_state", "after_state"):
                    row[key] = copy_json_card(row[key], old, new)
                conn.execute(tables["study_reviews"].insert().values(**row))
    for name in OWNED:
        t = tables[name]
        count = conn.scalar(select(func.count()).select_from(t).where(t.c.user_id == destination))
        if count != len(data[name]):
            raise ValueError(f"Copied row count mismatch in {name}")
    print("Replacement verified; committing transaction.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=int)
    parser.add_argument("destination", type=int)
    parser.add_argument("--destination-clerk-id", required=True, help="expected destination account's Clerk ID")
    parser.add_argument("--apply", action="store_true", help="replace destination data (default: preview only)")
    args = parser.parse_args()
    url = os.environ.get("DATABASE_URL")
    if not url:
        parser.error("DATABASE_URL must be explicitly set")
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    engine = create_engine(url)
    try:
        with engine.begin() as conn:
            run(conn, args.source, args.destination, args.destination_clerk_id, args.apply)
    except Exception as exc:
        print(f"Copy failed; no changes committed: {exc}", file=sys.stderr)
        return 1
    finally:
        engine.dispose()
    if args.apply:
        print("Replacement committed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
