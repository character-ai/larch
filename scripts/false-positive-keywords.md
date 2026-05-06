# false-positive-keywords.sh contract

## Purpose

`scripts/false-positive-keywords.sh` is a sourced-only Bash library that detects close-comment phrases indicating an issue is being closed as a false positive, duplicate, superseded, or won't-fix style outcome. Consumer: `/fix-issue`'s `issue-lifecycle.sh close --mark-false-positive-if-keyword` legacy fallback path. The v1 default has been replaced by the structured `--close-class` enum (see `skills/fix-issue/scripts/issue-lifecycle.md`); the keyword library remains the backstop for unstructured-prose close paths that have not migrated to the enum.

## API

`matches_false_positive_keywords <text>`

Exit codes:

- `0` — match.
- `1` — no match.
- `>=2` — helper failure. Stderr carries a diagnostic, and callers must not swallow this as "no match" unless they intentionally document that behavior.

## Matching Contract

The matcher first applies negation guards for `not duplicate`, `not a duplicate`, `not an duplicate`, `not false positive`, `not a false positive`, and hyphenated `false-positive` variants. These return `1` before any positive pattern is evaluated.

Positive phrases are case-insensitive:

- `won't fix` with straight or curly apostrophe (implemented with a portable no-whitespace slot between `won` and `t` rather than a multibyte bracket class).
- `wontfix`.
- `superseded` and `superseded by #<N>`.
- `not an issue`.
- `not a bug`.
- `duplicate of #<N>`. Bare `duplicate` is intentionally not a trigger.
- `false positive` and `false-positive`.

The phrase `not a bug` / `not an issue` exception is deliberate: those are closure reasons, unlike `not a duplicate` / `not a false positive`, which are negations of this marker class.

## Portability

Patterns must remain BSD+GNU portable. Do not use `\b` word boundaries; use explicit non-letter anchors such as `(^|[^a-z])` and `([^a-z]|$)`. The regression harness sources this library directly and must be updated with positive and negative fixtures whenever the pattern set changes.

## Edit-In-Sync

- `scripts/test-false-positive-keywords.sh` — direct regression harness for this library.
- `skills/fix-issue/scripts/issue-lifecycle.sh` — v1 consumer.
- `skills/fix-issue/scripts/issue-lifecycle.md` — consumer-facing trigger-order contract.
