## Decision 1: Scope of the fix
- **Question**: Beyond editing the two flag parsers in write-run-params.sh, what should be in scope?
- **Resolution**: Fix + tests + refactor. DRY the repeated missing/empty-value guard into a shared `require_value` helper used by all three boolean flags (`--partition-requested`, `--brainstorm-requested`, `--manual-gate-b`); add symmetric negative tests (partition/brainstorm empty + missing → exit 2 + stderr substring) to test-write-run-params.sh mirroring the existing manual-gate-b cases; sync write-run-params.md if it documents per-flag rejection.
- **Source**: user

## Decision 2: Out-of-file scope boundary
- **Question**: Should the change touch other scripts with similar `${2:?...}` patterns?
- **Resolution**: No. The OOS is scoped to `scripts/write-run-params.sh` only. Pre-existing inline guards on `--reason`/`--source`/`--sketch-budget`/`--review-budget`/`--workflow-path` (which intentionally allow empty values → null) are NOT refactored — only the three true/false boolean flags share the new helper.
- **Source**: codebase

## Decision 3: Behavior preservation
- **Question**: What existing behavior must not break?
- **Resolution**: Valid values (`true`/`false`) and enum-rejection (`maybe` → exit 2) must be unchanged. The only observable change is the missing/empty-value path: exit code 1→2 and message normalized to `write-run-params.sh: <flag> requires a value`. No production caller passes these flags without a value, and no existing test asserts the old exit-1 behavior, so no regression.
- **Source**: codebase
