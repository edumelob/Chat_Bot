"""Normalização de texto: minúsculas, sem acentos e sem pontuação."""
from __future__ import annotations

import re
import unicodedata

_SEPARATORS = re.compile(r"[^a-z0-9]+")

# Palavras que quase não ajudam a distinguir uma frase da outra (artigos, preposições, intensificadores).
# Pronomes como "meu/seu" e a negação "não" NÃO estão aqui de propósito: mudam o sentido da frase.
STOPWORDS = frozenset(
    {"a", "o", "as", "os", "um", "uma", "uns", "umas", "de", "do", "da", "dos", "das",
     "e", "em", "no", "na", "nos", "nas", "que", "para", "pra", "por", "ao", "aos",
     "muito", "bastante", "super", "favor", "agora", "tipo", "entao", "mesmo"}
)

# Abreviações comuns de chat, expandidas antes de comparar.
ABBREVIATIONS = {
    "vc": ["voce"], "vcs": ["voces"], "tb": ["tambem"], "tbm": ["tambem"], "pq": ["porque"],
    "q": ["que"], "oq": ["o", "que"], "blz": ["beleza"], "obg": ["obrigado"], "vlw": ["valeu"],
    "td": ["tudo"], "hj": ["hoje"], "msm": ["mesmo"], "n": ["nao"], "ta": ["esta"], "to": ["estou"],
}


def strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def words(text: str) -> list[str]:
    """'Olá, Vc está BEM?' -> ['ola', 'voce', 'esta', 'bem']"""
    result: list[str] = []
    for word in _SEPARATORS.split(strip_accents(text).lower()):
        if word:
            result.extend(ABBREVIATIONS.get(word, [word]))
    return result


def normalize(text: str) -> str:
    """Forma canônica usada para comparar frases (ignora acento, caixa e pontuação)."""
    return " ".join(words(text))


def tokenize(text: str) -> list[str]:
    """Palavras relevantes da frase. Se só sobrarem palavras comuns, mantém todas."""
    all_words = words(text)
    return [w for w in all_words if w not in STOPWORDS] or all_words
