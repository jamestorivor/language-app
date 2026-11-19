import pytest

from app.auth import current_user_id
from app.config import DEVELOPMENT_USER_ID
from app.main import app


@pytest.fixture(autouse=True)
def legacy_test_user(request):
    """Existing feature tests use their seeded local user; other tests require auth."""
    feature_tests = {
        "test_batch_word_lookup.py", "test_dictionary_expressions.py", "test_english_vocabulary.py", "test_english_study.py",
        "test_observability.py", "test_podcast_api.py", "test_routes.py", "test_study.py",
        "test_study_context.py", "test_study_policy_integration.py", "test_transcript_variant.py",
        "test_vocabulary_levels.py", "test_mark_known_progress.py",
    }
    if request.node.path.name in feature_tests:
        app.dependency_overrides[current_user_id] = lambda: DEVELOPMENT_USER_ID
    yield
    app.dependency_overrides.pop(current_user_id, None)
