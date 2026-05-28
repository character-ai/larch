## Proposed Design Outline

### Goals
- Fix SKILL.md ↔ `write-run-params.sh` contract drift (issue #3077 Section B) so `--simple`/`--hard` tier flags are no longer silently downgraded to HARD.
- Audit and fix all unsafe `${var//pat/$rep}` substitutions across repo shell scripts (bash 5.x `&`-corruption class — issue #3077 Section A).
- Add two CI linters that pin SKILL.md ↔ shipped-script contracts and renderer substitution safety going forward (issue #3077 Section C).

### Non-goals
- Schema migration of existing `run-params.json` files (additive schema v2→v3 only; new fields default-safe; readers tolerate v2 or v3).
- Behavior change to `/design` tier semantics (SIMPLE / HARD step-graph definitions unchanged).
- Refactoring unrelated SKILL.md call sites not touched by #3077's drift surface.

### Approach sketch
- **Section B (Option A)**: extend `scripts/write-run-params.sh` to accept `--reason`, `--source`, `--sketch-budget`, `--review-budget`, `--workflow-path`; bump `schema_version` 2→3 with corresponding JSON fields; update sibling `write-run-params.md`; extend `test-write-run-params.sh` with round-trip + default + invalid-value tests for each new flag.
- **Section B (silent-fallback abort)**: replace SKILL.md Step 0b "default to HARD sketch budget" recovery block with `printf '%s\n' '**⚠ /design: SKILL.md ↔ write-run-params.sh contract drift detected; aborting before silent tier downgrade.**' >&2; exit 1`.
- **Section A (audit + fix)**: grep every `.sh` under `scripts/` and `skills/*/scripts/` for `${VAR//pattern/$replacement}`; convert any site whose `$replacement` is file-derived to the `%%`/`##` split pattern (or add inline `# lint-renderer-safe: ok <reason>` for justified literals).
- **Section C (linters)**: add `scripts/lint-skill-md-flag-signature.sh` (extracts `--<flag>` args from invocations in `skills/*/SKILL.md` fenced shell blocks, asserts each appears in the target script's `case` block) and `scripts/lint-renderer-substitution-safety.sh` (flags unsafe `${var//pat/$rep}` callsites without justification comment). Both register in `make lint` and pre-commit; each ships a sibling `.md` and an offline harness.
- **BASH_AUTHORING.md §3 update**: document the `${var//pat/rep}` + `&` bash 5.x vs 3.x behavior split and require the `%%`/`##` split pattern in committed shell scripts.

### Surfaces in scope
- `scripts/write-run-params.sh` + sibling `scripts/write-run-params.md` + `scripts/test-write-run-params.sh`
- `skills/design/SKILL.md` (Step 0b fallback-abort replacement only; canonical 9-flag call site stays as-is)
- All `scripts/render-*.sh` and `skills/*/scripts/render-*.sh` (audit pass; convert unsafe sites)
- Other `.sh` files under `scripts/` and `skills/*/scripts/` if grep reveals additional unsafe sites
- New `scripts/lint-skill-md-flag-signature.sh` + sibling `.md` + harness `scripts/test-lint-skill-md-flag-signature.sh`
- New `scripts/lint-renderer-substitution-safety.sh` + sibling `.md` + harness `scripts/test-lint-renderer-substitution-safety.sh`
- `BASH_AUTHORING.md` (§3 amendment)
- `Makefile` (new `lint-skill-md-flag-signature` + `lint-renderer-substitution-safety` targets; register both in `make lint`)
- `.pre-commit-config.yaml` or `hooks/` (wire both new linters in)

### Open questions
- None.
