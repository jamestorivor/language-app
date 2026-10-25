from app.db.models import JapaneseDictionary, JapaneseReading, JapaneseSpelling, JapaneseWordFamiliarity
from app.schemas import GroupToken, UpdateFamiliarityScoreResponse, ParseJapaneseResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

def get_word_id(session : Session, wordToken : GroupToken) :
    lookup_form = wordToken.lookup_form
    word_id = session.scalar(select(JapaneseSpelling.word_id).where(JapaneseSpelling.spelling == lookup_form))

    if not word_id:
        word_id = session.scalar(select(JapaneseReading.word_id).where(JapaneseReading.reading == lookup_form))

    if not word_id:
        return None
    
    return word_id

def get_word_progress(session : Session, word_id: int, user_id : int) :
    familiarity_score = session.scalar(select(JapaneseWordFamiliarity.familiarity_score).where(JapaneseWordFamiliarity.word_id == word_id, JapaneseWordFamiliarity.user_id == user_id))
    if not familiarity_score:
        familiarity_score = 0
    return familiarity_score

def get_word_senses(session : Session, word_id : int):
    return session.scalar(select(JapaneseDictionary.senses).where(JapaneseDictionary.word_id == word_id))

def get_word_details(session: Session, wordToken : GroupToken, user_id : int):
    word_id = get_word_id(session, wordToken)
    if not word_id:
        return None
    familiarity_score = get_word_progress(session, word_id, user_id)
    senses = get_word_senses(session, word_id)

    return ParseJapaneseResponse(word_id=word_id, familiarity_score=familiarity_score, senses=senses)

def update_db_familiarity_score(session : Session, user_id : int, word_id : int, new_score : int) :
    progress = session.get(JapaneseWordFamiliarity, {"user_id":user_id, "word_id":word_id})

    if progress is None:
        progress = JapaneseWordFamiliarity(user_id=user_id, word_id=word_id,familiarity_score=new_score)
        session.add(progress)
    else:
        progress.familiarity_score = new_score

    session.commit()

    return UpdateFamiliarityScoreResponse(word_id=word_id, new_score=new_score)