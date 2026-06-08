## Proposed Design Outline

### Goals
- Run `/design` Step 3's full multi-round review as **one** script-internal Bash call that returns only on stop/cap or an enumerated bail-out — architectural parity with `/implement` Step 5.
- Apply per-round plan revisions in-loop via `revise-plan-with-waterfall.sh`; the main agent re-enters only on bail-outs and resumes with `--starting-round`.
- Shrink the Step-3 "Anti-halt continuation reminder" prose to the bail-out/resume boundaries only.

### Non-goals
- No change to review-panel composition, voting, scope-anchor handoff, or the cap-of-5 / reviewer-pruning / round-5 re-probe semantics.
- No change to `/implement` Step 5.
- No new git mechanism for revert — keep the reviser's `.before-revise` auto-revert plus existing snapshots.

### Approach sketch
- Extend `run-step3-review.sh` with `--mode loop` (mirrors `run-step5-review.sh`'s `--mode`).
- Add `review-design-step3-loop.sh` exposing `run_design_step3_loop()` `while true`, mirroring `review-implement-step5-loop.sh`.
- Per-round body (mechanical): `plan-review-loop.sh` → `revise-plan-with-waterfall.sh --patch-format file-replacement` → `gate-b-dedup-plan.sh` → `design-postplan-emit.sh --with-plan-size` → `snapshot-plan-round.sh` → `plan-review-continuation.sh`.
- Emit a `STEP3_REVIEW_LOOP_STATUS` envelope; bail-outs: `main-agent-vote-required`, `main-agent-apply-required`, `per-round-approval-required`, and `design-postplan-emit.sh` operator brakes.

### Surfaces in scope
- `skills/design/scripts/{run-step3-review, review-design-step3-loop (NEW), plan-review-loop, revise-plan-with-waterfall, plan-review-continuation, snapshot-plan-round}.sh`
- `skills/design/SKILL.md` Step 3 / 3.5; `skills/design/references/{plan-review, approval-gates}.md`; `docs/workflow-lifecycle.md`; `skills/shared/topology.tsv`.
- Harnesses: extend `test-run-step3-review.sh`, `test-plan-review-loop.sh`, `test-step3-review-cap.sh`, `test-design-pause-resume.sh`, `test-step3-orchestrator-fence.sh`; add `test-review-design-step3-loop.sh`; wire into `make lint` + `docs/linting.md`.

### Open questions
- None. The three open decisions are resolved (in-loop reviser; `--mode loop`; `--patch-format file-replacement`); git-per-round-commit dropped.
