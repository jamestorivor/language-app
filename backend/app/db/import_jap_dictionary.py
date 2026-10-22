import gzip
import xml.etree.ElementTree as ET
from config import DATA_PATH
from app.db.models import JapaneseDictionary, JapaneseReading, JapaneseSpelling
from app.db.session import SessionLocal
from typing import TypedDict
from sqlalchemy import select
from logging import Logger

logger = Logger(name="idk")

JAPANESE_DICTIONARY_FILE_NAME = "JMdict_e.gz"

class Spelling(TypedDict):
    position: int
    spelling: str
    info: list[str]
    priorities: list[str]


class Reading(TypedDict):
    position: int
    reading: str
    restricted_spellings: list[str]
    no_kanji: bool
    info: list[str]
    priorities: list[str]


class Sense(TypedDict):
    glosses: list[str]
    pos : list[str]
    stagk : list[str]
    stagr : list[str]
    s_inf : list[str]

class JMDictRecord(TypedDict):
    source_entry_id: int
    spellings: list[Spelling]
    readings: list[Reading]
    senses: list[Sense]

def required_text(element : ET.Element, tag : str) -> str:
    value = element.findtext(tag)

    if value is None or not value.strip():
        raise ValueError(f"Missing or empty <{tag}> inside <{element.tag}>")

    return value

def parse_entry(entry : ET.Element) -> JMDictRecord:
    return {
        "source_entry_id": int(required_text(entry, "ent_seq")),
        "spellings": [
            {
                "position" : position,
                "spelling" : required_text(element, "keb"),
                "info" : [info.text for info in element.findall("ke_inf")],
                "priorities" : [priority.text for priority in element.findall("ke_pri")]
            }
            for position, element in enumerate(entry.findall("k_ele"))
        ],
        "readings": [
            {
                "position" : position,
                "reading" : required_text(element, "reb"),
                "restricted_spellings" : [res_spell.text for res_spell in element.findall("re_restr")],
                "no_kanji" : element.find("re_nokanji") is not None,
                "info" : [info.text for info in element.findall("re_inf")],
                "priorities" : [priority.text for priority in element.findall("re_pri")]
            }
            for position, element in enumerate(entry.findall("r_ele"))
        ],
        "senses": [
            {
                "glosses": [
                    gloss.text
                    for gloss in sense.findall("gloss")
                ],
                "pos": [pos.text for pos in sense.findall("pos")],
                "stagk" : [stagk.text for stagk in sense.findall("stagk")],
                "stagr" : [stagr.text for stagr in sense.findall("stagr")],
                "s_inf" : [s_inf.text for s_inf in sense.findall("s_inf")]
            }
            for sense in entry.findall("sense")
        ],
    }

def construct_db_objects(record : JMDictRecord) -> JapaneseDictionary:
    return JapaneseDictionary(
            source_entry_id = record["source_entry_id"],
            spellings = [JapaneseSpelling(
                position = spelling["position"],
                spelling = spelling["spelling"],
                info = spelling["info"],
                priorities = spelling["priorities"]
            ) for spelling in record["spellings"]],
            readings = [JapaneseReading(
                reading = reading["reading"],
                position = reading["position"],
                restricted_spellings = reading["restricted_spellings"],
                no_kanji = reading["no_kanji"],
                info = reading["info"],
                priorities = reading["priorities"]
            )  for reading in record["readings"]],
            senses = record["senses"]
        )

def populate_dictionaries(records : list[JMDictRecord]) -> int:
    if not records:
        return 0
    with SessionLocal.begin() as session:
        source_ids = {
            record["source_entry_id"] for record in records
        }

        existing_ids = set(
            session.scalars(
                select(JapaneseDictionary.source_entry_id)
                .where(JapaneseDictionary.source_entry_id.in_(source_ids))
                )
                )

        new_words = []

        for record in records:
            source_id = record["source_entry_id"]
            if source_id in existing_ids:
                continue
            new_words.append(construct_db_objects(record))
            existing_ids.add(source_id)
        
        session.add_all(new_words)
    return len(new_words)

BATCH_SIZE = 500
def main():
    record_batch : list[JMDictRecord] = []
    batch_number = 0

    with gzip.open(DATA_PATH / JAPANESE_DICTIONARY_FILE_NAME, "rt", encoding='utf-8') as file:
        events = ET.iterparse(file, events=("start", "end"))
        _, root = next(events)

        for (event, element) in events:
            if event == "end" and element.tag == "entry":

                record = parse_entry(element)
                record_batch.append(record)

                root.remove(element)
                element.clear()

            if len(record_batch) >= BATCH_SIZE:
                n_inserted = populate_dictionaries(record_batch)
                batch_number += 1
                logger.info(f"Batch {batch_number} committed: inserted {n_inserted} new entries")
                record_batch.clear()

    if record_batch:
        inserted = populate_dictionaries(record_batch)
        batch_number += 1
        print(f"Batch {batch_number} committed: {inserted} new entries")


if __name__ == "__main__":
    main()

              
