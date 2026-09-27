# Project Context

This is a fork of [talktojev](https://github.com/xucian/talktojev), a classification-based chatbot.
There is no language model generating text. Responses are built word-by-word from discrete
classifier choices defined in `server.py`.

The only model is Jev, a decision model that chooses one option from a set. It cannot write a token.
Jev's behavior is governed entirely by Python data structures: `MOVES`, intent criteria, critique
criteria, and `instructions` strings passed to `decide()`.

## Fork Direction

This fork optimizes for straightforward, literal question-answering. A brief, accurate answer
is expected behavior, not a defect.

## Engineering Guidelines

- **Decision criteria** (`MOVES`, intent, critique, reflection) should be neutral and concise.
  Do not add elaboration, emotional language, or examples of undesired behavior to criteria strings.
- **Evaluation of output:** Measure clarity and accuracy, not conversational warmth or
  human-likeness. A terse correct answer scores well.
- **Avoid exaggeration** in both directions. Do not overstate what good behavior looks like,
  and do not unnecessarily elaborate on what bad behavior looks like.
- **Upstream boundaries:** This is a fork. Do not make claims about the upstream project's
  intentions or direction.
