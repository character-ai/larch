# test-lint-readability-preamble.sh contract

## Purpose

Regression harness for `scripts/lint-readability-preamble.sh`.

It proves the lint accepts a fully compliant fixture and rejects each supported variant independently.

## Fixture Shape

The harness stages `scripts/lint-readability-preamble.tsv` into each fixture root and derives paths from the same awk-based reader as the lint (see `scripts/lint-readability-preamble.tsv.md`). Helpers:

- `stage_manifest <root> [tsv-path]` — copy manifest into `$root/scripts/`
- `write_skill_md_with_steps <root> <count_per_step>` — SKILL.md with `<!-- step:2b|3b|4|5 -->` markers

Fixture cases:

- compliant: every manifest file satisfies its variant.
- external-bad / orchestrator-bad / orchestrator-partial / orchestrator-missing-file: baseline regressions.
- sketch-bare-token-rejected: four bare `<READABILITY_STYLE>` tokens without four sketch exact lines.
- placement-missing-step: file-level count passes; step `4` body lacks a directive.
- placement-correct: one directive in each of steps `2b`, `3b`, `4`, `5`.
- b6-extended / b6-negative: extra TSV row with/without matching fixture file.
- malformed-tsv: empty `expected_count` → lint exit 2.

## Assertions

The harness asserts exit codes and stderr substrings for each case above, plus manifest row-count parity (11 rows) with the repo TSV.

## Edit-in-sync

Update this file with `scripts/test-lint-readability-preamble.sh`, `scripts/lint-readability-preamble.sh`, `scripts/lint-readability-preamble.tsv`, and `scripts/lint-readability-preamble.md` when the manifest or accepted line patterns change.
