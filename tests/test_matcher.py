import pytest

from chatbot.matcher import Entry, Index, edit_distance


@pytest.mark.parametrize(
    "a, b, expected",
    [("nome", "nome", 0), ("nome", "nmoe", 1), ("gato", "rato", 1), ("", "abc", 3), ("abc", "", 3), ("ab", "ba", 1),
     ("casa", "casas", 1), ("kitten", "sitting", 3)],
)
def test_edit_distance(a, b, expected):
    assert edit_distance(a, b) == expected


def make_index():
    return Index([
        Entry("qual é o seu nome", ("Sou o Bot.",)),
        Entry("que horas são", ("Agora.",)),
        Entry("bom dia", ("Bom dia!",)),
    ])


def test_exact_match_scores_one_ignoring_accents_and_punctuation():
    match = make_index().best_match("QUE HORAS SAO???")
    assert match.entry.question == "que horas são"
    assert match.score == 1.0


def test_typos_are_corrected():
    index = make_index()
    assert index.best_match("qual é o seu nmoe").entry.question == "qual é o seu nome"
    assert index.best_match("bom dai") is not None  # 'dai' tem 3 letras: não é corrigida, mas não pode quebrar
    assert index.best_match("qeu horas sao").entry.question == "que horas são"


def test_correct_rules():
    index = make_index()
    assert index.correct(["boooom"]) == ["bom"]  # letras repetidas
    assert index.correct(["dai"]) == ["dai"]  # palavras curtas ficam como estão
    assert index.correct(["fome"]) == ["fome"]  # inicial diferente de 'nome': não corrige
    assert index.correct(["nmoe"]) == ["nome"]


def test_unknown_words_lower_the_score():
    index = make_index()
    known = index.best_match("qual é o seu nome").score
    with_unknown = index.best_match("qual é o seu nome de guerra").score
    assert known == 1.0 and with_unknown < 0.6


def test_completely_unrelated_text_scores_low():
    assert make_index().best_match("teoria da relatividade").score < 0.2


def test_no_tokens_or_no_entries_returns_none():
    assert make_index().best_match("???") is None
    assert Index([]).best_match("olá") is None


def test_learned_entry_wins_a_tie_against_base():
    index = Index([
        Entry("olá", ("resposta base",), "base"),
        Entry("olá", ("resposta aprendida",), "aprendido"),
    ])
    assert index.best_match("olá").entry.answers == ("resposta aprendida",)


def test_same_score_prefers_first_entry():
    index = Index([Entry("oi", ("primeira",)), Entry("olá", ("segunda",))])
    assert index.best_match("oi").entry.answers == ("primeira",)
