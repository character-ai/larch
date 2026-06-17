# test-bug-structure.sh — Contract

Structural regression test for `skills/bug/SKILL.md`. Pins the prompt-side `/bug --urgent` parsing contract and the forced `/issue --title-prefix` invocation used for both default and urgent bug reports.

## Purpose

`/bug` delegates filing to `/issue`. This harness prevents prompt drift where `/bug` stops stripping leading `--urgent`, stops forcing `[BUG]` prefixes, or bypasses `/issue --title-prefix` and reimplements prefix behavior locally.

## Assertions

| ID | What |
|----|------|
| A | Frontmatter `argument-hint` includes `[--urgent]` |
| B | The contract documents `--urgent` as the only flag |
| C | The obsolete "This skill has no flags" prose is absent |
| D | The contract strips leading `--urgent` tokens before validation |
| E | Step 5 includes `--title-prefix` in the `/issue` invocation |
| F | Both `[BUG]` and `[BUG] (URGENT)` literals appear |
| G | The skill still says not to pass `--no-dedup` |

## Makefile wiring

Wired into `test-harnesses` via `make test-bug-structure`.

## agent-lint.toml registration

Referenced only by `Makefile` and this sibling contract, not from runtime skill prose. Listed in `agent-lint.toml` under the Makefile-only harness pattern.

## Edit-in-sync rules

When modifying `skills/bug/SKILL.md` Step 5 or the flags contract:

1. Run `bash scripts/test-bug-structure.sh`.
2. Update this contract if load-bearing literals move.
3. Keep `/bug` on `/issue --title-prefix`. Do not reimplement prefix de-duplication.
