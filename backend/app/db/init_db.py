from app.db.session import Base, engine
from app.db.models import english_vocab, japanese_vocab, podcast, user

def main():
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    main()
