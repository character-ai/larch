# lint-readability-preamble.tsv

Tab-separated manifest consumed by `scripts/lint-readability-preamble.sh` and `scripts/test-lint-readability-preamble.sh`.

## Schema

Five columns on every data row (empty optional fields are literal empty strings, not omitted columns):

| Column | Meaning |
|---|---|
| `path` | Repo-relative file path |
| `variant` | `orchestrator-inline` or `external-prompt` |
| `expected_count` | Non-negative integer match count |
| `prompt_kind` | `standard`, `sketch`, or `plan-review` for external rows; empty for orchestrator rows |
| `step_markers` | Comma-separated step IDs for per-step placement checks; empty skips placement |

Comment lines (`#` in column 1) and blank lines are skipped.

## Shared reader contract

Both `lint-readability-preamble.sh` and `test-lint-readability-preamble.sh` MUST parse this file with the same awk filter and field extraction:

- Skip rows where `NF < 1`, column 1 matches `^#`, or the line is empty.
- Emit `path`, `variant`, `expected_count`, `prompt_kind`, `step_markers` via awk `FS="\t"` (never `IFS=$'\t' read`, which collapses empty middle fields).
- Reject `expected_count` when empty or non-digit (`''|*[!0-9]*` → exit 2 with a diagnostic naming the TSV path and row).

## Semantics

- **orchestrator-inline**: file-level count of the MANDATORY readability directive regex; when `step_markers` is non-empty, each listed step body (from `<!-- step:<id>` until the next `<!-- step:`) must contain at least one match.
- **external-prompt**: exact-line counts — `standard` and `plan-review` use backticked style lines; `sketch` uses the bare `Style requirements: <READABILITY_STYLE>.` line (no backticks).

## Edit in sync

When adding or renaming `/design` amendment sites, update this TSV, both consumers, `scripts/lint-readability-preamble.md`, and `skills/design/SKILL.md` step marker comments together. After a step ID rename, update `step_markers` on the SKILL.md row or placement lint fails closed with `step "<id>": ... marker not found`.
