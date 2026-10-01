from chatbot.text import normalize, strip_accents, tokenize, words


def test_strip_accents():
    assert strip_accents("Olá, ação, coração, pingüim") == "Ola, acao, coracao, pinguim"


def test_words_lowercase_no_punctuation():
    assert words("Olá, Você está BEM?!") == ["ola", "voce", "esta", "bem"]


def test_normalize_ignores_accent_case_and_punctuation():
    assert normalize("  Qual é o SEU nome???  ") == "qual e o seu nome"


def test_chat_abbreviations_are_expanded():
    assert words("vc tá bem? oq houve") == ["voce", "esta", "bem", "o", "que", "houve"]


def test_tokenize_removes_common_words():
    assert tokenize("Qual é o seu nome?") == ["qual", "seu", "nome"]


def test_tokenize_keeps_negation_and_pronouns():
    assert "nao" in tokenize("não estou bem")
    assert "meu" in tokenize("qual é o meu nome")


def test_tokenize_keeps_everything_when_only_common_words():
    assert tokenize("o que") == ["o", "que"]


def test_text_without_letters_has_no_tokens():
    assert tokenize("?? !!") == []
    assert normalize("😀") == ""
