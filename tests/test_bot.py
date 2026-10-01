import random

import pytest

from chatbot.bot import FALLBACK, MAX_MESSAGE_LENGTH, TOO_LONG, Chatbot
from chatbot.knowledge import LearnedStore
from conftest import FIXED_NOW


def test_original_conversation_is_understood(bot):
    assert bot.respond("Olá").text in {"Olá! Como você está?", "Oi! Tudo bem com você?"}
    assert bot.respond("Estou bem").text in {"Que bom!", "Fico feliz em saber!"}
    assert "Bot" in bot.respond("Qual é o seu nome?").text


def test_time_and_date_placeholders_use_the_clock(bot):
    assert bot.respond("que horas são?").text == "Agora são 14:35."
    assert bot.respond("qual é a data de hoje").text == "Hoje é terça-feira, 29/09/2026."


def test_custom_bot_name(store):
    ana = Chatbot(store=store, name="  Ana ", rng=random.Random(1), clock=lambda: FIXED_NOW)
    assert ana.name == "Ana"
    assert "Ana" in ana.respond("qual é o seu nome").text


@pytest.mark.parametrize(
    "message",
    [
        "Quanto é 2+2?", "qual é a capital da França", "qual o preço do bitcoin", "me fale sobre futebol",
        "qual é a sua cor favorita", "qual é o nome do meu cachorro", "quantos anos tem o seu pai",
        "asdfgh", "explique a teoria da relatividade", "estou com fome",
    ],
)
def test_unknown_questions_are_not_answered_with_something_wrong(bot, message):
    reply = bot.respond(message)
    assert reply.understood is False
    assert reply.text == FALLBACK


@pytest.mark.parametrize("message", ["", "   ", "???", "😀"])
def test_empty_or_symbol_only_messages_are_not_understood(bot, message):
    reply = bot.respond(message)
    assert reply.understood is False and reply.score == 0.0


@pytest.mark.parametrize(
    "message",
    ["oii", "OLÁ!!!", "como vc esta", "estou muito bem", "qual é o seu nmoe", "que horas sao agora",
     "conte uma piada por favor", "muito obrigada", "boa tade", "hj é que dia", "oq vc faz", "quem criuo voce"],
)
def test_variations_typos_and_abbreviations_are_understood(bot, message):
    assert bot.respond(message).understood is True


def test_negation_is_not_mistaken_for_the_positive_sentence(bot):
    assert "sinto muito" in bot.respond("não estou bem").text
    assert "sinto muito" in bot.respond("eu não estou bem hoje").text
    assert "sinto muito" not in bot.respond("estou bem").text


def test_learn_then_respond(bot):
    assert bot.respond("qual é a capital da França?").understood is False
    bot.learn("qual é a capital da França?", "Paris")
    reply = bot.respond("Qual a capital da frança")
    assert reply.understood is True and reply.text == "Paris"
    assert bot.learned_count == 1


def test_learned_answer_overrides_base_answer(bot):
    bot.learn("olá", "Salve, mestre!")
    assert bot.respond("olá").text == "Salve, mestre!"


def test_teaching_the_same_question_updates_the_answer(bot):
    bot.learn("cor do céu", "azul")
    bot.learn("Cor do céu?", "cinza")
    assert bot.learned_count == 1
    assert bot.respond("cor do céu").text == "cinza"


def test_learned_answers_can_use_placeholders(bot):
    bot.learn("que horário é esse", "Agora são {hora} de {data}")
    assert bot.respond("que horário é esse").text == "Agora são 14:35 de terça-feira, 29/09/2026"


@pytest.mark.parametrize("question, answer", [("", "x"), ("/x", "y"), ("pergunta", ""), ("???", "x")])
def test_learn_rejects_invalid_data(bot, question, answer):
    with pytest.raises(ValueError):
        bot.learn(question, answer)
    assert bot.learned_count == 0


def test_learning_survives_a_restart(tmp_path):
    path = tmp_path / "bot.sqlite3"
    with LearnedStore(path) as store:
        Chatbot(store=store).learn("qual é o meu time", "O melhor time do mundo")
    with LearnedStore(path) as store:
        assert Chatbot(store=store).respond("qual é o meu time").text == "O melhor time do mundo"


def test_threshold_controls_how_strict_the_bot_is(store):
    strict = Chatbot(store=store, threshold=1.0)
    assert strict.respond("quem fez voce").understood is False
    assert Chatbot(store=store, threshold=0.5).respond("quem fez voce").understood is True


@pytest.mark.parametrize("threshold", [0, -0.1, 1.1])
def test_invalid_threshold_raises(threshold):
    with pytest.raises(ValueError):
        Chatbot(threshold=threshold)


def test_empty_name_raises():
    with pytest.raises(ValueError):
        Chatbot(name="   ")


def test_same_seed_gives_same_random_choices(store):
    first = Chatbot(store=store, rng=random.Random(7))
    second = Chatbot(store=store, rng=random.Random(7))
    assert [first.respond("piada").text for _ in range(6)] == [second.respond("piada").text for _ in range(6)]


def test_bot_without_store_works_in_memory_and_closes_cleanly():
    bot = Chatbot()
    bot.learn("teste", "ok")
    assert bot.respond("teste").text == "ok"
    bot.close()


def test_very_long_messages_are_rejected_quickly(bot):
    reply = bot.respond("olá " * 500_000)
    assert reply.understood is False and reply.text == TOO_LONG
    assert bot.respond("a" * MAX_MESSAGE_LENGTH).text == FALLBACK  # no limite ainda é processada
    assert bot.respond("a" * (MAX_MESSAGE_LENGTH + 1)).text == TOO_LONG
