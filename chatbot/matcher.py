"""Busca da resposta mais parecida: TF-IDF + similaridade de texto + correção de erros de digitação."""
from __future__ import annotations

import difflib
import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Sequence

from .text import normalize, tokenize

COSINE_WEIGHT = 0.7  # peso da similaridade por palavras; o restante vem da similaridade do texto
MIN_TYPO_LENGTH = 4  # palavras menores que isso não são corrigidas (muito ambíguas)
_REPEATED_LETTERS = re.compile(r"(.)\1+")
ORIGIN_PRIORITY = {"base": 0, "aprendido": 1}  # em empate, o que o usuário ensinou vence


def edit_distance(a: str, b: str) -> int:
    """Distância de Damerau-Levenshtein: inserção, remoção, troca e inversão de letras vizinhas."""
    rows, cols = len(a) + 1, len(b) + 1
    d = [[0] * cols for _ in range(rows)]
    for i in range(rows):
        d[i][0] = i
    for j in range(cols):
        d[0][j] = j
    for i in range(1, rows):
        for j in range(1, cols):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                d[i][j] = min(d[i][j], d[i - 2][j - 2] + 1)
    return d[-1][-1]


@dataclass(frozen=True)
class Entry:
    """Uma pergunta conhecida e suas possíveis respostas."""

    question: str
    answers: tuple[str, ...]
    origin: str = "base"


@dataclass(frozen=True)
class Match:
    entry: Entry
    score: float


class Index:
    def __init__(self, entries: Sequence[Entry]):
        self.entries = list(entries)
        self._norms = [normalize(e.question) for e in self.entries]
        self._tokens = [tokenize(e.question) for e in self.entries]

        document_frequency: Counter[str] = Counter()
        for tokens in self._tokens:
            document_frequency.update(set(tokens))
        n = len(self.entries)
        self._idf = {t: math.log((1 + n) / (1 + df)) + 1 for t, df in document_frequency.items()}
        self._unknown_idf = math.log(1 + n) + 1  # palavra nunca vista = a mais "rara" possível
        self.vocabulary = tuple(sorted(self._idf))
        self._vectors = [self._vector(tokens) for tokens in self._tokens]

    def _vector(self, tokens: Sequence[str]) -> dict[str, float]:
        weights = {t: c * self._idf.get(t, self._unknown_idf) for t, c in Counter(tokens).items()}
        norm = math.sqrt(sum(w * w for w in weights.values()))
        return {t: w / norm for t, w in weights.items()} if norm else {}

    def _closest_word(self, token: str) -> str | None:
        """Palavra conhecida a no máximo 1 erro de distância (2 se a palavra for longa), com a mesma inicial."""
        max_distance = 1 if len(token) < 7 else 2
        candidates = [
            (edit_distance(token, word), word)
            for word in self.vocabulary
            if word[0] == token[0] and abs(len(word) - len(token)) <= max_distance
        ]
        candidates = [c for c in candidates if c[0] <= max_distance]
        return min(candidates)[1] if candidates else None

    def correct(self, tokens: Sequence[str]) -> list[str]:
        """Corrige palavras desconhecidas: 'oiii' -> 'oi', 'nmoe' -> 'nome'."""
        fixed = []
        for token in tokens:
            if token not in self._idf:
                collapsed = _REPEATED_LETTERS.sub(r"\1", token)
                if collapsed in self._idf:
                    token = collapsed
                elif len(token) >= MIN_TYPO_LENGTH:
                    token = self._closest_word(token) or token
            fixed.append(token)
        return fixed

    def best_match(self, text: str) -> Match | None:
        tokens = tokenize(text)
        if not tokens or not self.entries:
            return None

        normalized = normalize(text)
        corrected = self.correct(tokens)
        query = self._vector(corrected)
        query_text = " ".join(corrected)
        # Cada palavra que o bot nunca viu reduz a confiança: "qual a sua cor favorita" não deve
        # ser tratada como "qual a sua linguagem favorita".
        unknown = sum(1 for t in corrected if t not in self._idf)
        penalty = (1 - unknown / len(corrected)) ** 2

        best_key = None
        best: Match | None = None
        for i, entry in enumerate(self.entries):
            if normalized == self._norms[i]:
                score = 1.0
            else:
                cosine = sum(weight * self._vectors[i].get(t, 0.0) for t, weight in query.items())
                ratio = difflib.SequenceMatcher(None, query_text, " ".join(self._tokens[i])).ratio()
                score = (COSINE_WEIGHT * cosine + (1 - COSINE_WEIGHT) * ratio) * penalty
            key = (round(score, 12), ORIGIN_PRIORITY.get(entry.origin, 0), -i)
            if best_key is None or key > best_key:
                best_key, best = key, Match(entry, min(score, 1.0))
        return best
