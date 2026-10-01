import pytest

from chatbot.cli import main, run_chat


def session(bot, inputs):
    """Roda a conversa com entradas prontas. Quando acabam, simula o fim da entrada (EOF)."""
    remaining = list(inputs)
    output = []

    def read(prompt=""):
        if not remaining:
            raise EOFError
        item = remaining.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item

    run_chat(bot, read=read, write=output.append)
    return output


def test_greets_and_answers(bot):
    out = session(bot, ["olá", "para"])
    assert "Olá! Eu sou o Bot" in out[0]
    assert out[1] in {"Bot: Olá! Como você está?", "Bot: Oi! Tudo bem com você?"}
    assert out[-1] == "Bot: Até mais!"


@pytest.mark.parametrize("word", ["para", "PARA", "sair", "exit", "quit", "tchau", "Até logo", "ate mais!"])
def test_exit_words(bot, word):
    assert session(bot, [word, "olá"])[-1] == "Bot: Até mais!"
    # a mensagem depois da palavra de saída nunca é lida
    assert len(session(bot, [word, "olá"])) == 2


def test_eof_and_ctrl_c_end_gracefully(bot):
    assert session(bot, [])[-1] == "Bot: Até mais!"
    assert session(bot, [KeyboardInterrupt()])[-1] == "Bot: Até mais!"


def test_blank_lines_are_ignored(bot):
    out = session(bot, ["", "   ", "para"])
    assert out == [out[0], "Bot: Até mais!"]


def test_unknown_then_teach(bot):
    out = session(bot, ["qual é a capital da França?", "s", "Paris", "qual é a capital da França?", "para"])
    assert any("não sei responder" in line for line in out)
    assert any("Aprendido" in line for line in out)
    assert "Bot: Paris" in out


def test_unknown_and_decline_teaching(bot):
    out = session(bot, ["qual é a capital da França?", "n", "para"])
    assert not any("Aprendido" in line for line in out)
    assert bot.learned_count == 0


def test_cancel_teaching_with_empty_answer(bot):
    out = session(bot, ["qual é a capital da França?", "sim", "", "para"])
    assert any("cancelei" in line for line in out)
    assert bot.learned_count == 0


def test_teach_command(bot):
    out = session(bot, ["/ensinar", "qual é o meu time", "Palmeiras", "qual é o meu time", "para"])
    assert "Bot: Palmeiras" in out


def test_teach_command_can_be_cancelled(bot):
    out = session(bot, ["/ensinar", "", "para"])
    assert any("cancelei" in line for line in out)
    out = session(bot, ["/ensinar", "uma pergunta", "", "para"])
    assert any("cancelei" in line for line in out)
    assert bot.learned_count == 0


def test_teach_command_reports_invalid_question(bot):
    out = session(bot, ["/ensinar", "/proibido", "resposta", "para"])
    assert any("Não consegui aprender" in line for line in out)


def test_eof_in_the_middle_of_teaching(bot):
    assert session(bot, ["/ensinar", "pergunta"])[-1] == "Bot: Até mais!"


def test_help_and_unknown_command(bot):
    out = session(bot, ["/ajuda", "/AJUDA", "/xyz", "para"])
    assert sum("/ensinar" in line for line in out) == 2
    assert any("Comando desconhecido" in line for line in out)


def test_main_creates_database_and_returns_zero(tmp_path):
    db = tmp_path / "dados" / "bot.sqlite3"
    inputs = iter(["olá", "para"])
    out = []
    code = main(["--db", str(db), "--nome", "Ana"], read=lambda p="": next(inputs), write=out.append)
    assert code == 0
    assert db.exists()
    assert "Eu sou o Ana" in out[0]


def test_main_with_memory_database_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert main(["--db", ":memory:"], read=lambda p="": "para", write=lambda s: None) == 0
    assert list(tmp_path.iterdir()) == []


def test_main_unwritable_database_returns_error(tmp_path, capsys):
    blocker = tmp_path / "arquivo"
    blocker.write_text("x")
    assert main(["--db", str(blocker / "x" / "bot.sqlite3")]) == 1
    assert "banco de dados" in capsys.readouterr().err


def test_main_rejects_invalid_arguments(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--limiar", "2"])
    assert exc.value.code == 2
    with pytest.raises(SystemExit):
        main(["--limiar", "abc"])
    assert main(["--nome", "  ", "--db", ":memory:"]) == 2


def test_main_accepts_decimal_comma_in_threshold():
    assert main(["--db", ":memory:", "--limiar", "0,7"], read=lambda p="": "para", write=lambda s: None) == 0


def test_long_message_gets_warning_and_no_teaching_offer(bot):
    out = session(bot, ["x" * 600, "para"])
    assert any("longa demais" in line for line in out)
    assert not any("ensinar" in line for line in out)
