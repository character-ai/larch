## Decision 1: Section B fix path (write-run-params.sh signature drift)
- **Question**: Option A (extend script with 5 new flags + schema v2→v3) vs Option B (trim SKILL.md and inline-derive downstream fields)?
- **Resolution**: Option A — extend `scripts/write-run-params.sh` to accept `--reason`, `--source`, `--sketch-budget`, `--review-budget`, `--workflow-path`; bump `schema_version` from 2 to 3; add corresponding JSON fields; extend `scripts/test-write-run-params.sh` to assert new flags + new JSON keys.
- **Source**: user

## Decision 2: Section A scope (${var//pat/$rep} + bash 5.x &)
- **Question**: render-*.sh audit only, or repo-wide scan + linter?
- **Resolution**: Repo-wide scan + linter — scan every .sh file under `scripts/` and `skills/*/scripts/` for `${var//pat/$rep}` where `$rep` is file-derived; convert unsafe sites to %%/## split; add a linter that catches all such callers (not just renderers).
- **Source**: user

## Decision 3: Silent-downgrade fallback (SKILL.md Step 0b recovery branch)
- **Question**: Convert "fall back to HARD" recovery to a loud abort in this PR, or defer?
- **Resolution**: Convert in this PR — once contract drift is fixed by Option A, the fallback never legitimately fires; converting to abort prevents future drift from being silently swallowed. Replace the in-memory HARD-default block in `skills/design/SKILL.md` (~line 312) with an abort + clear error message.
- **Source**: user

## Decision 4: Section C regression scaffolding (linters)
- **Question**: Include flag-signature linter, renderer-safety linter, both, or minimal targeted test?
- **Resolution**: Both linters — (i) SKILL.md ↔ shipped-script flag-signature linter (catches Section B class); (ii) ${var//pat/$rep} renderer-safety linter (catches Section A class). Register both in `make lint` and pre-commit hook.
- **Source**: user

## Decision 5: Sibling .md contract updates
- **Question**: Should sibling `.md` contract docs be updated alongside script changes?
- **Resolution**: Yes — per `.claude/rules/script-md-siblings.md` (repo-wide rule), every script change requires sibling .md update in the same PR. Applies to `scripts/write-run-params.md` (extend to document new flags + schema v3) and any new linter .md siblings.
- **Source**: codebase

## Decision 6: Test harness pattern for new flags
- **Question**: How should `scripts/test-write-run-params.sh` cover the new flags?
- **Resolution**: Mirror existing patterns — round-trip tests for each new flag, default-value tests, invalid-value rejection tests. Follow the same shape as the existing `--partition-requested` test cases. Additive only — existing test cases continue to pass.
- **Source**: codebase

## Decision 7: SKILL.md call-site preservation
- **Question**: Should the canonical Step 0b call site in SKILL.md remain unchanged with Option A?
- **Resolution**: Yes — Option A keeps the SKILL.md Step 0b call site as-is (9 flags). The script-side change is fully backward-compatible because callers passing only `--classification` + `--output` still get a valid schema-v3 doc with defaults; callers passing the full flag set now succeed instead of failing.
- **Source**: codebase

## Decision 8: SKILL.md ↔ script flag-signature linter mechanics
- **Question**: What's the canonical implementation pattern for the SKILL.md ↔ shipped-script flag-signature linter?
- **Resolution**: Bash harness under `scripts/` that walks all `skills/*/SKILL.md` files, finds invocation patterns of the form `${CLAUDE_PLUGIN_ROOT}/scripts/<name>.sh` (and `skills/*/scripts/<name>.sh`) inside fenced bash/sh/shell blocks, extracts every `--<flag>` arg used, then greps the target script's `case` block for matching `--<flag>) ` lines. Output: actionable diff on regression; exit 0 when all flags resolve, non-zero otherwise.
- **Source**: codebase

## Decision 9: Renderer ${var//pat/$rep} linter mechanics
- **Question**: How should the renderer-safety linter detect unsafe `${var//pat/$rep}` callers?
- **Resolution**: Extend `make lint-bash32` (or add a new harness under `scripts/`) that greps every `.sh` file under `scripts/` and `skills/*/scripts/` for `${VAR//pattern/$replacement}` constructs where `$replacement` is a file-derived variable. Flag any such caller unless it has an inline `# lint-renderer-safe: ok <reason>` justification comment OR uses the `%%`/`##` split pattern. Hook into `make lint` and pre-commit.
- **Source**: codebase
