## Proposed Design Outline

### Goals
- Make `cleanup.sh` top-level enumeration `find` failures visible via `larch_err` (end the silent fail-open) on BOTH the cache and `/tmp` passes.
- Fix the Step 3 regression: remove the dead `LARCH_DESIGN_CONVERGENCE_THRESHOLD` / `--convergence-threshold` plumbing end-to-end so `run-step3-review.sh` stops forwarding a flag `plan-review-loop.sh` rejects.
- Keep docs, tests, and `SECURITY.md` truthful and in sync with both behavior changes.

### Non-goals
- Items #3255 and #3260b: already resolved — recorded as evidence-backed no-ops, no edits.
- No change to normal cleanup retention, the `maxdepth 5` nested confirm, or the cache-vs-`/tmp` `-mtime +N` asymmetry.
- No change to the hardcoded single-round convergence rule itself (`_round_qualifies_for_convergence`).

### Approach sketch
- `cleanup.sh`: redirect each enumeration `find` to a temp file, branch on its exit (warn on failure), then read NUL-delimited from the temp file. Bash 3.2-safe; normal path preserved.
- Remove `--convergence-threshold` from `run-step3-review.sh` (argv parse, required-check, forward) and from the `SKILL.md` Step 3 call; drop env-var docs.
- Tests: new `test-cleanup.sh` enumeration-failure stub keyed on `-mindepth 1`; new `run-step3-review` integration-seam test using a loop stub that mirrors the real reject-unknown contract; update stale `--convergence-threshold` assertions.

### Surfaces in scope
- `skills/cleanup/scripts/`: `cleanup.sh`, `cleanup.md`, `test-cleanup.sh`
- `skills/design/scripts/`: `run-step3-review.sh`, `run-step3-review.md`, `test-run-step3-review.sh`, `test-step3-review-cap.sh`
- `skills/design/SKILL.md`, `skills/design/references/flags.md`
- `docs/configuration-and-permissions.md`, `SECURITY.md`

### Open questions
- None.
