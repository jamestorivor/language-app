from sqlalchemy import Boolean, Integer, JSON, text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base

class User(Base):
    __tablename__ = "users"

    id : Mapped[int] = mapped_column(primary_key=True)
    name : Mapped[str]
    fsrs_retention_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=90, server_default=text('90'))
    fsrs_maximum_interval: Mapped[int] = mapped_column(Integer, nullable=False, default=36500, server_default=text('36500'))
    fsrs_fuzzing: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text('true'))
    study_shortcuts: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # date_created : ???
