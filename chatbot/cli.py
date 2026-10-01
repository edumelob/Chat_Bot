"""Interface de terminal: python -m chatbot"""
from __future__ import annotations

import argparse
import sys
from typing import Callable

from . import __version__
from .bot import DEFAULT_THRESHOLD, Chatbot
from .knowledge import MAX_QUESTION_LENGTH, KnowledgeError, LearnedStore
from .text import normalize

DEFAULT_DB = "dados/chatbot.sqlite3"
PROMPT = "Você: "
EXIT_WORDS = frozenset({"para", "sair", "exit", "quit", "tchau", "ate logo", "ate mais"})
YES_WORDS = frozenset({"s", "sim", "y", "yes"})

HELP_TEXT = """Comandos:
  /ajuda     mostra esta mensagem
  /ensinar   ensina uma nova pergunta e resposta
  para       encerra a conversa (também: sair, tchau, exit)
Se eu não souber responder, posso aprender com você e lembrar na próxima vez."""


def is_exit(message: str) -> bool:
    return normalize(message) in EXIT_WORDS


def _ask(read: Callable[[str], str], prompt: str) -> str | None:
    """Lê uma linha; devolve None se o usuário só apertou Enter (cancelar)."""
    text = read(prompt).strip()
    return text or None


def _teach(bot: Chatbot, question: str, read, write) -> None:
    answer = _ask(read, PROMPT)
    if answer is None:
        write(f"{bot.name}: Tudo bem, cancelei.")
        return
    try:
        bot.learn(question, answer)
    except ValueError as exc:
        write(f"{bot.name}: Não consegui aprender isso: {exc}")
        return
    write(f"{bot.name}: Aprendido! Agora sei responder isso.")


def _teach_command(bot: Chatbot, read, write) -> None:
    write(f"{bot.name}: Qual pergunta ou frase você quer que eu aprenda? (Enter para cancelar)")
    question = _ask(read, PROMPT)
    if question is None:
        write(f"{bot.name}: Tudo bem, cancelei.")
        return
    write(f"{bot.name}: E o que devo responder quando alguém disser isso?")
    _teach(bot, question, read, write)


def _offer_teaching(bot: Chatbot, message: str, read, write) -> None:
    write(f"{bot.name}: Quer me ensinar a responder isso? (s/n)")
    if normalize(read(PROMPT)) not in YES_WORDS:
        return
    write(f"{bot.name}: Qual deve ser a minha resposta? (Enter para cancelar)")
    _teach(bot, message, read, write)


def run_chat(
    bot: Chatbot,
    read: Callable[[str], str] = input,
    write: Callable[[str], None] = print,
) -> None:
    """Loop da conversa. `read` e `write` podem ser trocados (útil nos testes)."""
    write(f"{bot.name}: Olá! Eu sou o {bot.name}. Digite /ajuda para ver os comandos ou 'para' para sair.")
    while True:
        try:
            message = read(PROMPT).strip()
        except (EOFError, KeyboardInterrupt):
            write("")
            write(f"{bot.name}: Até mais!")
            return

        if not message:
            continue
        if is_exit(message):
            write(f"{bot.name}: Até mais!")
            return

        try:
            if message.startswith("/"):
                command = message.split()[0].lower()
                if command == "/ajuda":
                    write(HELP_TEXT)
                elif command == "/ensinar":
                    _teach_command(bot, read, write)
                else:
                    write(f"{bot.name}: Comando desconhecido. Digite /ajuda para ver os comandos.")
                continue

            reply = bot.respond(message)
            write(f"{bot.name}: {reply.text}")
            if not reply.understood and len(message) <= MAX_QUESTION_LENGTH:
                _offer_teaching(bot, message, read, write)
        except (EOFError, KeyboardInterrupt):
            write("")
            write(f"{bot.name}: Até mais!")
            return


def _limiar(value: str) -> float:
    try:
        number = float(value.replace(",", "."))
    except ValueError:
        raise argparse.ArgumentTypeError(f"{value!r} não é um número") from None
    if not 0 < number <= 1:
        raise argparse.ArgumentTypeError("o limiar deve estar entre 0 (exclusivo) e 1")
    return number


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="chatbot",
        description="Chatbot em português que aprende com você.",
    )
    parser.add_argument("--nome", default="Bot", help="nome do bot (padrão: Bot)")
    parser.add_argument(
        "--db",
        default=DEFAULT_DB,
        metavar="CAMINHO",
        help=f"arquivo SQLite onde o bot guarda o que aprendeu (padrão: {DEFAULT_DB}); use :memory: para não gravar nada",
    )
    parser.add_argument(
        "--limiar",
        type=_limiar,
        default=DEFAULT_THRESHOLD,
        metavar="N",
        help=f"confiança mínima para responder, de 0 a 1 (padrão: {DEFAULT_THRESHOLD})",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: list[str] | None = None, read=input, write=print) -> int:
    # Evita UnicodeEncodeError/UnicodeDecodeError em terminais com codificação limitada
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError, OSError):
            pass

    args = build_parser().parse_args(argv)
    if not args.nome.strip():
        print("Erro: o nome do bot não pode ser vazio.", file=sys.stderr)
        return 2

    try:
        store = LearnedStore(args.db)
    except KnowledgeError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1

    try:
        bot = Chatbot(store=store, name=args.nome, threshold=args.limiar)
    except (KnowledgeError, ValueError) as exc:
        store.close()
        print(f"Erro: {exc}", file=sys.stderr)
        return 1

    try:
        run_chat(bot, read=read, write=write)
    finally:
        store.close()
    return 0
