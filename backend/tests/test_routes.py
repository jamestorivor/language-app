from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_parse_returns_grouped_words_with_lookup_forms_and_original_spans():
    text = "超えたからかもしれません。"
    response = client.get("/jap/parse", params={"text": text})

    assert response.status_code == 200
    groups = response.json()
    assert [(group["text"], group["lookup_form"]) for group in groups] == [
        ("超えた", "超える"),
        ("から", "から"),
        ("かもしれません", "かもしれない"),
        ("。", "。"),
    ]
    assert [token["text"] for token in groups[0]["tokens"]] == ["超え", "た"]
    assert "".join(group["text"] for group in groups) == text
    for group in groups:
        assert text[group["start_idx"]:group["end_idx"]] == group["text"]

