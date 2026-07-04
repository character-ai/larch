# lint-readability-preamble.tsv

Tab-separated manifest consumed by `python3 python/cli.py lint readability-preamble` and `python/tests/lint/test_lint_readability_preamble.py`.

## Schema

Five columns on every data row. Empty optional fields are literal empty strings, not omitted columns.

| Column | Meaning |
|---|---|
| `path` | Repo-relative file path, or `__metadata__` for metadata rows |
| `variant` | `orchestrator-inline`, `external-prompt`, `metadata-min-count`, or `skill-exempt` |
| `expected_count` | Non-negative integer match count, floor value, or `0` for exemptions |
| `prompt_kind` | `standard` or `plan-review` for external rows; exemption reason for `skill-exempt`; empty otherwise |
| `step_markers` | Comma-separated step IDs for per-step placement checks; optional exemption reason fallback |

Comment lines (`#` in column 1) and blank lines are skipped.

## Shared reader contract

Both `python3 python/cli.py lint readability-preamble` and the Python test consumer MUST parse this file with equivalent row filtering and field extraction:

- Skip rows where column 1 matches `^#` or the line is empty.
- Emit `path`, `variant`, `expected_count`, `prompt_kind`, `step_markers` by splitting on literal tab characters without collapsing empty middle fields.
- Reject `expected_count` when empty or non-digit (`''|*[!0-9]*` → exit 2 with a diagnostic naming the TSV path and row).

## Semantics

- **orchestrator-inline**: file-level count of the MANDATORY readability directive with the correct root path form. Public `skills/**` rows must use `${CLAUDE_PLUGIN_ROOT}/skills/shared/readability-style.md`. Dev-only `.claude/skills/**` rows must use `$PWD/skills/shared/readability-style.md`. When `step_markers` is non-empty, each listed step body (from `<!-- step:<id>` until the next `<!-- step:`) must contain at least one match.
- **external-prompt**: exact prompt-line counts. `standard` and `plan-review` use backticked `<READABILITY_STYLE>` lines.
- **metadata-min-count**: committed floor for the sum of `expected_count` values across counted rows. Lowering the floor is an explicit diff.
- **skill-exempt**: explicit opt-out for a `SKILL.md` file that composes no prose. `expected_count` must be `0` and a reason is required in `prompt_kind` or `step_markers`.

## Dynamic skill coverage

The lint walks public `skills/*/SKILL.md` and dev-only `.claude/skills/*/SKILL.md` files. Each file must contain the correct shared readability path unless it has a `skill-exempt` row. New skills fail until they add a directive or an exemption row.
The lint also walks `agents/code-reviewer.md` and `agents/reviewer-*.md`, so reviewer agents must carry the public shared readability path.

## Edit in sync

When adding or renaming readability amendment sites, update this TSV, the Python lint/test consumers, and any structural harness pins together. After a step ID rename, update `step_markers` on the row or placement lint fails closed with `step "<id>": ... marker not found`.
