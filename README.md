# Chatbot Inteligente (Python)

Chatbot de terminal em português que **entende variações e erros de digitação, admite quando não sabe e aprende com você**, guardando o que aprendeu em um banco SQLite. Não usa bibliotecas de IA: o motor de busca de respostas é implementado do zero com a biblioteca padrão do Python.

> É um chatbot de **recuperação de respostas** (compara a sua frase com perguntas conhecidas), não uma IA generativa como o ChatGPT. Ele só responde o que conhece ou o que você ensinou.

## Funcionalidades

- Responde por **similaridade** (TF-IDF + similaridade de texto), ignorando acentos, maiúsculas e pontuação
- Entende **abreviações** (`vc`, `hj`, `oq`, `vlw`...) e **erros de digitação** (`nmoe` vira `nome`, `oiii` vira `oi`)
- Diz **"não sei"** quando a confiança é baixa, em vez de responder qualquer coisa
- **Aprende**: quando não sabe, você pode ensinar a resposta, e ele lembra nas próximas conversas (SQLite)
- Respostas dinâmicas: hora, data e o nome do bot (`--nome`)
- Sem dependências para rodar: apenas Python 3.10+
- 130+ testes automatizados (`pytest`), incluindo testes que executam o programa de verdade

## Como executar

```bash
git clone (https://github.com/edumelob/Chat_Bot)
cd Chat Bot
python -m chatbot
```

No Windows, use `py -m chatbot` se `python` não for reconhecido. Não é preciso instalar nada.

### Opções

| Opção | Descrição |
|-------|-----------|
| `--nome NOME` | Nome do bot (padrão: `Bot`) |
| `--db CAMINHO` | Arquivo SQLite com o que o bot aprendeu (padrão: `dados/chatbot.sqlite3`). Use `:memory:` para não gravar nada |
| `--limiar N` | Confiança mínima para responder, de 0 a 1 (padrão: `0.6`). Maior = mais cauteloso |
| `--version`, `--help` | Versão e ajuda |

### Comandos dentro da conversa

| Comando | O que faz |
|---------|-----------|
| `/ajuda` | Lista os comandos |
| `/ensinar` | Ensina uma nova pergunta e resposta |
| `para`, `sair`, `tchau`, `exit` | Encerra a conversa (Ctrl+C também funciona) |

## Exemplo de conversa

```text
Bot: Olá! Eu sou o Bot. Digite /ajuda para ver os comandos ou 'para' para sair.
Você: Olá
Bot: Olá! Como você está?
Você: qual é o seu nmoe?
Bot: Meu nome é Bot.
Você: Quanto é 2+2?
Bot: Desculpe, ainda não sei responder isso.
Bot: Quer me ensinar a responder isso? (s/n)
Você: s
Bot: Qual deve ser a minha resposta? (Enter para cancelar)
Você: É 4
Bot: Aprendido! Agora sei responder isso.
Você: quanto é 2+2
Bot: É 4
Você: que horas sao?
Bot: Agora são 14:35.
Você: qual é a capital da França?
Bot: Desculpe, ainda não sei responder isso.
Bot: Quer me ensinar a responder isso? (s/n)
Você: n
Você: me conta uma piada
Bot: Qual é o cúmulo da programação? Um loop infinito de trabalho.
Você: para
Bot: Até mais!
```

Tudo que você ensina (como o "É 4" acima) fica salvo em `dados/chatbot.sqlite3` e continua valendo na próxima vez que abrir o bot.

## Como funciona

1. **Normalização** (`text.py`): minúsculas, remoção de acentos e pontuação, expansão de abreviações e remoção de palavras vazias (`o`, `de`, `que`...). Pronomes (`meu`/`seu`) e a negação (`não`) são mantidos, pois mudam o sentido.
2. **Correção** (`matcher.py`): palavras desconhecidas são trocadas pela palavra conhecida mais próxima (distância de Damerau-Levenshtein), só para palavras com 4+ letras e a mesma inicial.
3. **Pontuação** (`matcher.py`): `70% similaridade de cosseno TF-IDF + 30% similaridade de texto`. Cada palavra que o bot nunca viu **reduz a confiança**, para que "qual é a sua *cor* favorita" não seja confundida com "qual é a sua *linguagem* favorita".
4. **Decisão** (`bot.py`): abaixo do limiar (0,6) o bot diz que não sabe e oferece aprender. Se uma pergunta aprendida empata com a base, a aprendida vence.
5. **Persistência** (`knowledge.py`): o que você ensina vai para o SQLite (`INSERT ... ON CONFLICT DO UPDATE`), então ensinar a mesma pergunta de novo atualiza a resposta.

O limiar (0,6) foi escolhido testando dezenas de frases: variações corretas de perguntas conhecidas ficam acima dele e perguntas fora do assunto ficam bem abaixo. Se o bot estiver cauteloso ou ousado demais para você, ajuste com `--limiar`.

## Testes

```bash
pip install -r requirements-dev.txt
python -m pytest
```

Cobrem normalização, motor de busca, base de conhecimento, banco de dados, o bot, a interface de terminal e execuções ponta a ponta do programa (incluindo terminais com codificação limitada e banco corrompido). A CI do GitHub roda tudo em Linux com Python 3.10, 3.11 e 3.12.

## Estrutura

```
.
├── chatbot/
│   ├── __main__.py              # python -m chatbot
│   ├── cli.py                   # conversa no terminal e argumentos
│   ├── bot.py                   # classe Chatbot
│   ├── matcher.py               # TF-IDF, similaridade e correção de digitação
│   ├── knowledge.py             # base fixa (JSON) + aprendizado (SQLite)
│   ├── text.py                  # normalização de texto
│   └── base_conhecimento.json   # perguntas e respostas de fábrica
├── tests/
└── .github/workflows/ci.yml
```

Para ensinar algo de fábrica ao bot, adicione um grupo em `chatbot/base_conhecimento.json` (`perguntas` e `respostas`). Nas respostas você pode usar `{nome}`, `{hora}` e `{data}`.

## Limitações conhecidas

- Não entende contexto entre mensagens: cada frase é avaliada sozinha.
- Só reconhece o que se parece com uma pergunta conhecida; não gera texto novo.
- A negação só é tratada bem quando existe uma entrada para ela (ex.: "não estou bem").
- Palavras com menos de 4 letras não têm correção de digitação.
- Mensagens acima de 500 caracteres são recusadas.

## Próximos passos

- Memória de contexto (lembrar o que foi dito antes na conversa)
- Interface web simples (Flask ou FastAPI)
- Exportar e importar o conhecimento aprendido

## Licença

[MIT](LICENSE)
