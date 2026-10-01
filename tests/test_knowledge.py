import json

import pytest

from chatbot.knowledge import (
    BASE_FILE,
    MAX_ANSWER_LENGTH,
    MAX_QUESTION_LENGTH,
    PLACEHOLDERS,
    KnowledgeError,
    LearnedStore,
    load_base,
    validate_teaching,
)
from chatbot.text import normalize


def write_base(tmp_path, content):
    path = tmp_path / "base.json"
    path.write_text(content if isinstance(content, str) else json.dumps(content), encoding="utf-8")
    return path


def test_shipped_base_is_valid():
    entries = load_base(BASE_FILE)
    assert len(entries) >= 50
    assert len({normalize(e.question) for e in entries}) == len(entries)  # sem perguntas repetidas


def test_shipped_base_only_uses_supported_placeholders():
    import re

    for entry in load_base(BASE_FILE):
        for answer in entry.answers:
            for found in re.findall(r"\{[^}]*\}", answer):
                assert found in PLACEHOLDERS, f"placeholder desconhecido {found!r} em {answer!r}"


def test_base_covers_the_original_conversation():
    questions = {normalize(e.question) for e in load_base()}
    assert {"ola", "estou bem", "qual e o seu nome"} <= questions


@pytest.mark.parametrize(
    "content",
    [
        "isto não é json",
        [],
        {"outra_chave": []},
        {"entradas": "texto"},
        {"entradas": [{"perguntas": [], "respostas": ["x"]}]},
        {"entradas": [{"perguntas": ["a"], "respostas": []}]},
        {"entradas": [{"perguntas": ["a"], "respostas": ["  "]}]},
        {"entradas": [{"perguntas": [1], "respostas": ["x"]}]},
        {"entradas": [{"perguntas": ["??"], "respostas": ["x"]}]},
        {"entradas": [{"perguntas": ["Olá"], "respostas": ["x"]}, {"perguntas": ["ola!"], "respostas": ["y"]}]},
        {"entradas": ["texto"]},
    ],
)
def test_invalid_base_files_raise(tmp_path, content):
    with pytest.raises(KnowledgeError):
        load_base(write_base(tmp_path, content))


def test_missing_base_file_raises(tmp_path):
    with pytest.raises(KnowledgeError):
        load_base(tmp_path / "nao_existe.json")


@pytest.mark.parametrize(
    "question, answer",
    [
        ("", "x"), ("   ", "x"), ("???", "x"), ("/comando", "x"),
        ("pergunta", ""), ("pergunta", "   "),
        ("p" * (MAX_QUESTION_LENGTH + 1), "x"), ("pergunta", "r" * (MAX_ANSWER_LENGTH + 1)),
    ],
)
def test_validate_teaching_rejects_bad_input(question, answer):
    with pytest.raises(ValueError):
        validate_teaching(question, answer)


def test_validate_teaching_trims():
    assert validate_teaching("  oi  ", "  olá  ") == ("oi", "olá")


def test_store_save_and_list(store):
    assert store.count() == 0
    store.save("Qual é a capital da França?", "Paris")
    entries = store.all()
    assert store.count() == 1
    assert entries[0].question == "Qual é a capital da França?"
    assert entries[0].answers == ("Paris",)
    assert entries[0].origin == "aprendido"


def test_store_upsert_by_normalized_question(store):
    store.save("Capital da França?", "Lyon")
    store.save("capital da franca", "Paris")
    assert store.count() == 1
    assert store.all()[0].answers == ("Paris",)


def test_store_rejects_invalid_teaching(store):
    with pytest.raises(ValueError):
        store.save("/x", "y")
    assert store.count() == 0


def test_store_persists_between_openings_and_creates_folders(tmp_path):
    path = tmp_path / "pasta" / "sub" / "bot.sqlite3"
    with LearnedStore(path) as first:
        first.save("pergunta", "resposta")
    with LearnedStore(path) as second:
        assert [(e.question, e.answers) for e in second.all()] == [("pergunta", ("resposta",))]


def test_store_unwritable_location_raises_knowledge_error(tmp_path):
    blocker = tmp_path / "arquivo"
    blocker.write_text("x")
    with pytest.raises(KnowledgeError):
        LearnedStore(blocker / "sub" / "bot.sqlite3")


def test_store_accepts_unicode_and_quotes(store):
    store.save("Você gosta de 'café' e \"chá\"? ☕", "Gosto de ambos; DROP TABLE learned; --")
    assert store.count() == 1
    assert "DROP TABLE" in store.all()[0].answers[0]
