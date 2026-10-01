"""Conhecimento do bot: base fixa (JSON) + o que o usuário ensinou (SQLite)."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .matcher import Entry
from .text import normalize

BASE_FILE = Path(__file__).with_name("base_conhecimento.json")
PLACEHOLDERS = ("{nome}", "{hora}", "{data}")
MAX_QUESTION_LENGTH = 200
MAX_ANSWER_LENGTH = 500

_SCHEMA = """
CREATE TABLE IF NOT EXISTS learned (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    question      TEXT NOT NULL,
    question_norm TEXT NOT NULL UNIQUE,
    answer        TEXT NOT NULL,
    created_at    TEXT NOT NULL
)
"""


class KnowledgeError(Exception):
    """Problema com a base de conhecimento ou com o banco de dados."""


def load_base(path: str | Path = BASE_FILE) -> list[Entry]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise KnowledgeError(f"Não foi possível ler a base de conhecimento ({path}): {exc}") from exc

    groups = data.get("entradas") if isinstance(data, dict) else None
    if not isinstance(groups, list):
        raise KnowledgeError("A base de conhecimento precisa ter a lista 'entradas'.")

    entries: list[Entry] = []
    seen: set[str] = set()
    for number, group in enumerate(groups, start=1):
        questions = group.get("perguntas") if isinstance(group, dict) else None
        answers = group.get("respostas") if isinstance(group, dict) else None
        if not (isinstance(questions, list) and questions and all(isinstance(q, str) for q in questions)):
            raise KnowledgeError(f"Entrada {number}: 'perguntas' deve ser uma lista de textos.")
        if not (isinstance(answers, list) and answers and all(isinstance(a, str) and a.strip() for a in answers)):
            raise KnowledgeError(f"Entrada {number}: 'respostas' deve ser uma lista de textos não vazios.")
        for question in questions:
            key = normalize(question)
            if not key:
                raise KnowledgeError(f"Entrada {number}: pergunta vazia ou sem letras: {question!r}")
            if key in seen:
                raise KnowledgeError(f"Pergunta repetida na base de conhecimento: {question!r}")
            seen.add(key)
            entries.append(Entry(question, tuple(answers), "base"))
    return entries


def validate_teaching(question: str, answer: str) -> tuple[str, str]:
    """Valida e limpa um par pergunta/resposta ensinado pelo usuário."""
    question, answer = question.strip(), answer.strip()
    if not normalize(question):
        raise ValueError("A pergunta precisa conter pelo menos uma letra ou número.")
    if question.startswith("/"):
        raise ValueError("A pergunta não pode começar com '/', pois isso é reservado para comandos.")
    if len(question) > MAX_QUESTION_LENGTH:
        raise ValueError(f"A pergunta é longa demais (máximo de {MAX_QUESTION_LENGTH} caracteres).")
    if not answer:
        raise ValueError("A resposta não pode ficar vazia.")
    if len(answer) > MAX_ANSWER_LENGTH:
        raise ValueError(f"A resposta é longa demais (máximo de {MAX_ANSWER_LENGTH} caracteres).")
    return question, answer


class LearnedStore:
    """Guarda em SQLite o que o usuário ensinou. Use ':memory:' para não gravar nada em disco."""

    def __init__(self, path: str | Path = "dados/chatbot.sqlite3"):
        self.path = str(path)
        try:
            if self.path != ":memory:":
                Path(self.path).expanduser().parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(self.path)
            self._conn.execute(_SCHEMA)
            self._conn.commit()
        except (OSError, sqlite3.Error) as exc:
            raise KnowledgeError(f"Não foi possível abrir o banco de dados '{self.path}': {exc}") from exc

    def all(self) -> list[Entry]:
        rows = self._conn.execute("SELECT question, answer FROM learned ORDER BY id").fetchall()
        return [Entry(question, (answer,), "aprendido") for question, answer in rows]

    def count(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM learned").fetchone()[0]

    def save(self, question: str, answer: str) -> None:
        """Grava (ou atualiza, se a pergunta já existir) um par pergunta/resposta."""
        question, answer = validate_teaching(question, answer)
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        try:
            with self._conn:
                self._conn.execute(
                    "INSERT INTO learned (question, question_norm, answer, created_at) VALUES (?, ?, ?, ?) "
                    "ON CONFLICT(question_norm) DO UPDATE SET "
                    "question = excluded.question, answer = excluded.answer, created_at = excluded.created_at",
                    (question, normalize(question), answer, now),
                )
        except sqlite3.Error as exc:
            raise KnowledgeError(f"Não foi possível gravar no banco de dados: {exc}") from exc

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "LearnedStore":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()
