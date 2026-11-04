from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base

class User(Base):
    __tablename__ = "users"

    id : Mapped[int] = mapped_column(primary_key=True)
    name : Mapped[str]
    # date_created : ???