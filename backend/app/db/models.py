from sqlalchemy import CheckConstraint, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from app.db.session import Base

from typing import Any

class User(Base):
    __tablename__ = "users"

    id : Mapped[int] = mapped_column(primary_key=True)
    name : Mapped[str]
    # date_created : ???

class JapaneseDictionary(Base):
    __tablename__ = "japanese_dictionary"

    word_id : Mapped[int] = mapped_column(primary_key=True)
    # JMdict's ent_seq.
    source_entry_id: Mapped[int] = mapped_column(unique=True)

    # Meanings, glosses, parts of speech, notes, and sense restrictions.
    senses: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)

    spellings: Mapped[list["JapaneseSpelling"]] = relationship(
        back_populates="entry",
        cascade="all, delete-orphan",
        order_by="JapaneseSpelling.position",
    )

    readings: Mapped[list["JapaneseReading"]] = relationship(
        back_populates="entry",
        cascade="all, delete-orphan",
        order_by="JapaneseReading.position",
    )

class JapaneseSpelling(Base):
    __tablename__ = "japanese_spellings"

    word_id: Mapped[int] = mapped_column(
        ForeignKey("japanese_dictionary.word_id"),
        primary_key=True,
    )

    # Decided from import order
    # Original order within the JMdict entry.
    position: Mapped[int]

    # JMDict : keb 
    # represents the written form of the word usually in kanji
    spelling: Mapped[str] = mapped_column(
        Text, primary_key=True, index=True
    )

    # JMDict : ke_inf
    # Additional information about the spelling (irregular, outdated etc...)
    info: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)

    # JMDict : ke_pri
    # Priority markers representing the relative commonness of the spelling
    priorities: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)

    entry: Mapped["JapaneseDictionary"] = relationship(
        back_populates="spellings"
    )

class JapaneseReading(Base):
    __tablename__ = "japanese_readings"

    word_id: Mapped[int] = mapped_column(
        ForeignKey("japanese_dictionary.word_id"),
        primary_key=True,
    )

    # Decided from import order
    # Original order within the JMDict dictionary 
    position: Mapped[int]

    # JMDict : reb
    # Kana reading of the entry
    reading: Mapped[str] = mapped_column(
        Text, primary_key=True, index=True
    )

    # JMDict : re_restr 
    # spellings this reading applies to.
    restricted_spellings: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list
    )

    # JMDict : re_nokanji
    # If the reading has a kanji form
    no_kanji: Mapped[bool] = mapped_column(default=False)

    # JMDict : re_inf
    # Additional information about the reading (irregular, outdated etc...)
    info: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)

    # JMDict : re_pri
    # Priority markers representing the relative commonness of the reading
    priorities: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)

    entry: Mapped["JapaneseDictionary"] = relationship(
        back_populates="readings"
    )

class JapaneseWordFamiliarity(Base):
    __tablename__ = "user_japanese_word_progress"

    user_id : Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    word_id : Mapped[int] = mapped_column(ForeignKey("japanese_dictionary.word_id"),primary_key=True)
    familiarity_score : Mapped[int] 

    __table_args__ = (
        CheckConstraint(
            "familiarity_score BETWEEN 1 AND 5",
            name="valid_familiarity_score"
        ),
    )