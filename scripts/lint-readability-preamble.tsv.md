# lint-readability-preamble.tsv

Tab-separated manifest consumed by `python3 python/cli.py lint readability-preamble` and `python/test_lint_readability_preamble.py`.

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

Both `python3 python/cli.py lint readability-preamble` and `python/test_lint_readability_preamble.py` MUST parse this file with equivalent row filtering and field extraction:

- Skip rows where `NF < 1`, column 1 matches `^#`, or the line is empty.
- Emit `path`, `variant`, `expected_count`, `prompt_kind`, `step_markers` by splitting on literal tab characters without collapsing empty middle fields.
- Reject `expected_count` when empty or non-digit (`''|*[!0-9]*` → exit 2 with a diagnostic naming the TSV path and row).

## Semantics

- **orchestrator-inline**: file-level count of the MANDATORY readability directive regex; when `step_markers` is non-empty, each listed step body (from `<!-- step:<id>` until the next `<!-- step:`) must contain at least one match.
- **external-prompt**: exact prompt-line counts — `standard` and `plan-review` use backticked style lines; `sketch` uses the bare `Style requirements: <READABILITY_STYLE>.` line (no backticks), either as a literal line or as the escaped `\n...` tail in the byte-preserved sketch prompt bodies.

## Edit in sync

When adding or renaming `/design` amendment sites, update this TSV, the Python lint/test consumers and `skills/design/SKILL.md` step marker comments together. After a step ID rename, update `step_markers` on the SKILL.md row or placement lint fails closed with `step "<id>": ... marker not found`.
