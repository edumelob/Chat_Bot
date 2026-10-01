"""O chatbot: encontra a resposta mais parecida e aprende novas."""
from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from .knowledge import LearnedStore, load_base
from .matcher import Entry, Index

DEFAULT_THRESHOLD = 0.6
FALLBACK = "Desculpe, ainda não sei responder isso."
MAX_MESSAGE_LENGTH = 500  # evita que textos enormes deixem o bot lento
TOO_LONG = f"Sua mensagem é longa demais (máximo de {MAX_MESSAGE_LENGTH} caracteres). Tente algo mais curto."
WEEKDAYS = ("segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo")


@dataclass(frozen=True)
class Reply:
    text: str
    understood: bool
    score: float


class Chatbot:
    def __init__(
        self,
        store: LearnedStore | None = None,
        name: str = "Bot",
        threshold: float = DEFAULT_THRESHOLD,
        rng: random.Random | None = None,
        clock: Callable[[], datetime] | None = None,
        base_entries: list[Entry] | None = None,
    ):
        if not name.strip():
            raise ValueError("O nome do bot não pode ser vazio.")
        if not 0 < threshold <= 1:
            raise ValueError("O limiar de confiança deve estar entre 0 (exclusivo) e 1.")
        self.name = name.strip()
        self.threshold = threshold
        self._owns_store = store is None
        self._store = store or LearnedStore(":memory:")
        self._base = list(base_entries) if base_entries is not None else load_base()
        self._rng = rng or random.Random()
        self._clock = clock or datetime.now
        self._index = self._build_index()

    def _build_index(self) -> Index:
        return Index(self._base + self._store.all())

    def _fill(self, text: str) -> str:
        now = self._clock()
        values = {
            "{nome}": self.name,
            "{hora}": now.strftime("%H:%M"),
            "{data}": f"{WEEKDAYS[now.weekday()]}, {now.strftime('%d/%m/%Y')}",
        }
        for placeholder, value in values.items():
            text = text.replace(placeholder, value)
        return text

    def respond(self, message: str) -> Reply:
        if len(message) > MAX_MESSAGE_LENGTH:
            return Reply(TOO_LONG, False, 0.0)
        match = self._index.best_match(message)
        if match is None or match.score < self.threshold:
            return Reply(FALLBACK, False, match.score if match else 0.0)
        return Reply(self._fill(self._rng.choice(match.entry.answers)), True, match.score)

    def learn(self, question: str, answer: str) -> None:
        """Ensina uma nova resposta (grava no banco). Levanta ValueError se os dados forem inválidos."""
        self._store.save(question, answer)
        self._index = self._build_index()

    @property
    def learned_count(self) -> int:
        return self._store.count()

    def close(self) -> None:
        if self._owns_store:
            self._store.close()
