import random
from datetime import datetime

import pytest

from chatbot.bot import Chatbot
from chatbot.knowledge import LearnedStore

# Terça-feira, 29/09/2026, 14:35
FIXED_NOW = datetime(2026, 9, 29, 14, 35)


@pytest.fixture
def store():
    with LearnedStore(":memory:") as s:
        yield s


@pytest.fixture
def bot(store):
    return Chatbot(store=store, rng=random.Random(42), clock=lambda: FIXED_NOW)
