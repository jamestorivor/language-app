from sqlalchemy import CheckConstraint, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class EnglishDictionary(Base):
    __tablename__ = "english_dictionary"

    word_id: Mapped[int] = mapped_column(primary_key=True)
    headword: Mapped[str] = mapped_column(Text, unique=True)
    lookup_key: Mapped[str] = mapped_column(Text, index=True)
    meaning: Mapped[str] = mapped_column(Text)


class EnglishWordFamiliarity(Base):
    __tablename__ = "user_english_word_progress"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    word_id: Mapped[int] = mapped_column(ForeignKey("english_dictionary.word_id"), primary_key=True)
    familiarity_score: Mapped[int]

    __table_args__ = (
        CheckConstraint("familiarity_score BETWEEN 1 AND 5", name="valid_english_familiarity_score"),
    )
