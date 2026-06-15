# tokenizer

A tiny tokenizer for arithmetic expressions.

## API contract

- `tokenize(text)` -> list of `(kind, value)` tuples. `kind` is one of
  `NUMBER`, `OP`, `UNKNOWN`. Numbers include decimals written `.5` and `1.`.
- `token_count(text)` -> the EXACT number of tokens in `text`.
- `kinds(text)` -> a list of the token **kind strings**, e.g. `["NUMBER","OP"]`.

Any character that is not a digit, `.`, or one of `+ - * /` MUST tokenize as
`UNKNOWN`. The tokenizer never guesses an operator.
