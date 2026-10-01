"""Testes ponta a ponta: executam `python -m chatbot` de verdade, como o usuário faria."""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(stdin_text, *args, io_encoding="utf-8"):
    env = {**os.environ, "PYTHONIOENCODING": io_encoding}
    env.pop("PYTHONUTF8", None)
    return subprocess.run(
        [sys.executable, "-m", "chatbot", *args],
        input=stdin_text.encode("utf-8"), capture_output=True,
        cwd=ROOT, env=env, timeout=60,
    )


def text(data):
    return data.decode("utf-8", errors="replace")


def test_runs_and_exits_cleanly():
    result = run("olá\npara\n", "--db", ":memory:")
    assert result.returncode == 0, text(result.stderr)
    assert "Bot:" in text(result.stdout) and "Até mais!" in text(result.stdout)
    assert result.stderr == b""


def test_version_and_help():
    assert "chatbot 1.0.0" in text(run("", "--version").stdout)
    assert "--db" in text(run("", "--help").stdout)


def test_learning_persists_across_separate_runs(tmp_path):
    db = str(tmp_path / "bot.sqlite3")
    first = run("qual é a capital da França?\ns\nParis\npara\n", "--db", db)
    assert first.returncode == 0, text(first.stderr)
    assert "Aprendido" in text(first.stdout)

    second = run("qual é a capital da França?\npara\n", "--db", db)
    assert second.returncode == 0, text(second.stderr)
    assert "Bot: Paris" in text(second.stdout)


def test_end_of_input_without_exit_command_does_not_crash():
    result = run("olá\n", "--db", ":memory:")
    assert result.returncode == 0 and b"Traceback" not in result.stderr


def test_terminals_with_limited_encodings_do_not_crash():
    for encoding in ("ascii", "cp1252", "cp850", "latin-1"):
        result = run("Olá, você é um robô?\npara\n", "--db", ":memory:", io_encoding=encoding)
        assert result.returncode == 0, (encoding, text(result.stderr))
        assert b"Traceback" not in result.stderr


def test_database_errors_are_reported_without_traceback(tmp_path):
    broken = tmp_path / "quebrado.db"
    broken.write_text("isto não é um banco sqlite")
    result = run("oi\n", "--db", str(broken))
    assert result.returncode == 1
    assert b"Traceback" not in result.stderr and "banco de dados" in text(result.stderr)
