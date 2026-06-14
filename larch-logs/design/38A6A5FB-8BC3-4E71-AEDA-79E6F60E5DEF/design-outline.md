## Proposed Design Outline

### Goals
- Prevent `/design` from publishing `[DESIGNED]` when zero reviewers ran (hard stop on `panel-init-failed`).
- Write `review_status:` and `rounds_completed:` into every `larch:plan` block so downstream tooling can verify review provenance.
- Fix six supporting bugs (mechanical_churn typo tolerance, scope anchor pre-guard, stale worktree cleanup, feature-description.txt on replace path, failure reporter COMPOSE_STATUS requirement, `/implement` Preflight block on explicit bad `review_status:`).

### Non-goals
- Redesign the plan-review panel dispatch or reviewer slot logic.
- Change Gate C UX beyond the mandatory warning already requested in the issue.
- Apply `review_status:` retroactively to existing `[DESIGNED]` issues or require re-design.

### Approach sketch
- Add `panel-init-failed` status: detect it in `plan_review_panel.py` (or `plan_review.py`) when no `plan-review/round-1/` exists; propagate through `design-step3-review.sh` result env.
- Guard in `design-step3-entry-state.sh`: create and validate `plan-review-scope-anchor.txt` before the background loop launches; abort with a clear error if absent or empty.
- Hard-stop in `SKILL.md` Step 3 branch matrix: route `panel-init-failed` to `SUMMARY_OUTCOME=failed-publish` (or new status), run Final summary block, do not continue to Gate C.
- Write `review_status:` / `rounds_completed:` in `design-step5c.sh` (via `design-publish.sh`) before plan-block composition.
- Add `/implement` Preflight guard: refuse when `review_status:` is explicitly `panel-init-failed` or `panel-skipped`.
- Fix `plan_quality.py` `check-plan-size`: auto-normalize `mechanical_churn: <integer>` to `true`.
- Fix `design-step0-init.sh`: write `feature-description.txt` on the `already-planned→replace` path (when `_init_route` is `already-planned` but operator chose Replace).
- Fix `design-log-publish.sh`: detect stale same-RUN_ID worktree, prune it, retry before failing.
- Fix `design-failure-report.sh`: file issue on `panel-failed`/`panel-init-failed` regardless of `COMPOSE_STATUS`.

### Surfaces in scope
- `python/plan_quality.py` (Bug 1: mechanical_churn normalizer)
- `python/plan_review_panel.py` or `python/plan_review.py` (Bug 3: panel-init-failed status)
- `skills/design/scripts/design-step3-entry-state.sh` (Bug 2: scope anchor pre-guard)
- `skills/design/scripts/design-step3-review.sh` (Bug 2/3: propagate panel-init-failed)
- `skills/design/SKILL.md` (Bug 3: hard-stop branch matrix)
- `skills/design/scripts/design-publish.sh` or `design-step5c.sh` (Bug 4: write review_status: / rounds_completed:)
- `skills/implement/SKILL.md` Preflight section (Bug 4: refuse explicit bad review_status:)
- `python/issue_wire.py` or `python/named_block.py` or `python/cli.py named-block write` (Bug 4: plan block schema update)
- `skills/design/scripts/design-step0-init.sh` (Bug 6: feature-description.txt on replace path)
- `scripts/design-log-publish.sh` (Bug 5: stale worktree cleanup)
- `skills/design/scripts/design-failure-report.sh` (Bug 7: COMPOSE_STATUS gate removal)
- Test files for each changed Python module and script

### Open questions
- None.
