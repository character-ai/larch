## Decision 1: Launcher-invoked wrapper disposition
- **Question**: Keep launcher-invoked Step-3 `.sh` files as thin bash, or delete them and repoint SKILL.md to direct `cli.py`?
- **Resolution**: Keep thin wrappers. Move heavy logic into `python/plan_review.py` / `python/plan_review_panel.py`. Leave launcher-invoked wrappers (`design-step3-review.sh`, `design-step35.sh`, `design-step35-settle.sh`, `design-step3b-entry.sh`, `design-step3b-sanitize.sh`, `design-step3b-tail.sh`, `design-step3-entry.sh`, `design-step3-entry-preview.sh`, `design-step3-entry-state.sh`, `design-step3-mav.sh`, `design-step3-continuation-entry.sh`, `design-step3-gate-b-bypass.sh`) as thin bash that calls new `cli.py plan-review` verbs and keeps session rehydration + pause checks. Preserves the SKILL.md launcher contract.
- **Source**: user

## Decision 2: Behavior latitude during the port
- **Question**: Strict bug-for-bug parity, or allow inline fixes?
- **Resolution**: Allow opportunistic low-risk fixes and simplifications during the port. Still preserve pause/resume marker bytes and `docs/issue-anchored-plan.md` payload compatibility exactly.
- **Source**: user

## Decision 3: Scope of `_run_legacy` removal
- **Question**: Port only the listed on-disk scripts, or fully eliminate the legacy shim?
- **Resolution**: Full removal. Port every body `_run_legacy()` dispatches so `_run_legacy`, `_LEGACY_ASSETS` / gzip blobs, `import gzip`, and `_materialize_legacy_root` are deleted from `python/plan_review.py`. Meets the issue Definition of Done.
- **Source**: issue DoD + codebase

## Decision 4: Pure internal bodies (not launcher-invoked) are deleted
- **Question**: What about scripts SKILL.md does not invoke through the launcher?
- **Resolution**: Delete outright after porting (`review-design-step3-loop.sh`, `plan-review-continuation.sh`, `lib-step3-prelaunch-failure.sh`, and any gzip-embedded bodies such as `run-step3-review.sh`, `plan-review-loop.sh`, `dispatch-plan-review-panel.sh`, `dispatch-plan-voters.sh`, `emit-plan.sh`, `finalize-plan.sh`, the preview script, `design-step3-state.sh`, `record-plan-review-round-timing.sh`, `gate-b-dedup-plan.sh`, `lib-drift-baseline.sh`, `lib-design-round-artifacts.sh`). Logic moves into Python. No stubs.
- **Source**: issue + recipe

## Decision 5: Consumer cutover + retirement bookkeeping
- **Question**: Which consumers get repointed, and what bookkeeping is required?
- **Resolution**: Follow the sh-to-py recipe. Repoint all consumers (SKILL.md, `skills/design/references/*.md`, Makefile targets, CI, other helpers) to direct `cli.py plan-review` verbs. Delete retired `.sh` + `test-*.sh` harness + `.md` siblings. Append deleted paths to `python/migrated-scripts.tsv`. Move test coverage into `python/test_plan_review.py` / `python/test_plan_review_panel.py`. Pass `make lint-retired-scripts`.
- **Source**: docs/python-migration.md recipe

## Decision 6: Hard constraints and non-goals
- **Question**: What must not break, and what is out of scope?
- **Resolution**: Hard constraints: preserve pause/resume marker bytes; preserve `docs/issue-anchored-plan.md` payload fields; preserve the `STEP3_REVIEW_LOOP_STATUS` envelope grammar, exit codes, and result-env contracts (`.step3-review-result.env`, `.step3-review-cap.env`); preserve `review-round-count.txt` persist/rollback semantics. Non-goals: do not re-port `tally` (done in #4433); do not change Step 3 panel composition or voting thresholds; do not touch unrelated /design steps; keep `design-step3-review.sh` as the Step-3 process-group wrapper.
- **Source**: issue DoD + C3a1 note + codebase

Decisions resolved: 6 (2 from user, 4 from issue/codebase/recipe).
