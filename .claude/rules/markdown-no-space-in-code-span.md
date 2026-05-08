---
paths: ["**/*.md"]
---

# Markdown Code Spans — No Inner Whitespace

Inside a backtick code span, content must not start or end with
whitespace. `markdownlint` MD038 (enabled by default; see
`.markdownlint.json`) blocks lint CI on violations; MD037 covers
`*emphasis*` / `_emphasis_` boundaries.

When rendering a literal that begins or ends with a space, such as an
exact-match prefix grammar:

- **Drop the surrounding code span** when the token is clear in context:
  write `Umbrella:` (no trailing space) instead of encoding a trailing
  space inside the span.
- **HTML entities are not a workaround.** Encoding boundary whitespace as
  `&nbsp;` inside the span usually fails MD038 because the rule reads
  source whitespace, not rendered HTML. Move the literal space outside:
  write the inner token without whitespace and put the space in prose.
- **Use a code fence** for multi-token / multi-line literals where exact
  whitespace matters; fences are exempt from MD038.
- **Describe boundary spacing in prose** instead of encoding it inside the
  span: write the span without literal whitespace and qualify nearby
  ("the prefix `Umbrella:` followed by a single space").

This rule covers all `.md` files. Historical violations often appear in
`CHANGELOG.md` entries quoting prefix grammars verbatim and `SKILL.md`
files documenting literal markers.

Related: `MD001/heading-increment` (no h1 → h3 jumps) is the same hygiene
class; when adding a section, increment by exactly one level from the
surrounding context.
