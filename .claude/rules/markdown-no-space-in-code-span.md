---
paths: ["**/*.md"]
---

# Markdown Code Spans — No Inner Whitespace

Inside a backtick code span, the content must not start or end with whitespace. The `markdownlint` MD038 rule (enabled by default, see `.markdownlint.json`) blocks the lint CI job when violated; MD037 covers the same pattern for `*emphasis*` / `_emphasis_` boundaries.

When you need to render a literal that begins or ends with a space (for example, an exact-match prefix grammar):

- **Drop the surrounding code span** when the content is already a recognizable token in context: write `Umbrella:` (no trailing space) instead of trying to encode a trailing space inside the span.
- **HTML entities are not a workaround.** `&nbsp;` rendered inside a code span still trips MD038 when adjacent to a real space. Move the literal space outside the span instead — write the inner token without whitespace and put the space in the surrounding prose.
- **Code fence** for multi-token / multi-line literals where exact whitespace matters; fences are exempt from MD038.
- **Backslash-escape the rendering boundary**: write the span without the literal whitespace and clarify in surrounding prose ("the prefix `Umbrella:` followed by a single space").

This rule covers all `.md` files. The most common violations historically are in `CHANGELOG.md` entries that quote prefix grammars verbatim and `SKILL.md` files that document literal markers.

Related: `MD001/heading-increment` (no h1 → h3 jumps) is the same hygiene class — when adding a section, increment by exactly one level from the surrounding context.
