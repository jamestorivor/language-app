from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine

DATABASE_URL = "postgresql://user:admin@localhost:5435/japdb"

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autoflush=False,bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
