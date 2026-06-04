## Proposed Design Outline

### Goals
- Collapse the per-plan-write `design-postplan-emit.sh` → `check-plan-size.sh` two-Bash-turn pattern into one call via an additive `--with-plan-size` mode, at all three prompt-side emit sites (initial Step 2b, Gate B §Shared post-apply pipeline, discussion-round2 / Step 1e Gate A re-entry rewrite).
- Save 1 turn per plan write (compounds across review rounds) plus a per-turn output-token + determinism win.
- Collapse the Step 2b consumption fence to the Phase 1 thin-fence contract (call → echo → branch-on-rc).

### Non-goals
- No change to `check-plan-size.sh` threshold logic or its standalone callability (still used by `plan-review-loop.sh` and as a separate script).
- No behavior change to any rare branch (validator defects, hard size trigger, `--partition`, soft mechanical-churn advisory) — pure turn-saving on the clean path.
- No change to pause/resume semantics; no revert of the #3441 classification-stderr preservation fix.

### Approach sketch
- Add `--with-plan-size` to `design-postplan-emit.sh`: after a successful emit + (optional) snapshot + validate, invoke the real `check-plan-size.sh`, surface its trigger KVs, and map the merged verdict to thin-fence action exit codes.
- The driver owns clean-path display (soft-advisory + under-threshold breadcrumb); the orchestrator fence branches on exit code only for LLM-tool actions (defects / hard-trigger / partition / pause).
- Without the flag the driver keeps its exact current {0,1,2} contract (backward-compat for any non-merged caller).

### Surfaces in scope
- `skills/design/scripts/design-postplan-emit.{sh,md}`; `check-plan-size.{sh,md}` (add caller note only).
- `skills/design/SKILL.md` Step 2b / 2b.5; `references/approval-gates.md` Gate B; `references/discussion-rounds.md` round-2; `references/flags.md`.
- Harnesses: `test-design-postplan-emit.{sh,md}`, `test-check-plan-size.{sh,md}` (as needed), `scripts/test-design-structure.sh`; `Makefile` if a target is missing.

### Open questions
- Exit-code action mapping + co-occurrence priority (defects vs hard-trigger vs partition) — resolved in the plan, vetted by plan review.
- Driver invokes `check-plan-size.sh` via `$PLUGIN_ROOT` (consistent; needs harness symlink) vs `$SCRIPT_DIR` (sibling-local) — resolved in the plan.
