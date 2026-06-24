## Goal
Implement issue #5156: [IMPLEMENTING] md-to-py-IV: collapse the design Step 3 post-loop matrix to one NEXT_ACTION and retire legacy --mode single prose.

## Implementation Plan
## Plan

Implement the approved loop-only Step 3 routing change with minimum scope. Collapse the post-loop branch matrix to a single authoritative `NEXT_ACTION=` directive emitted and persisted by Python. Retire legacy `--mode single` prose only after harness pins are updated first.

Key constraints: keep `STEP3_REVIEW_LOOP_STATUS`, `LOOP_STATUS`, and loop behavior unchanged for diagnostics and mid-loop resume; add deterministic `NEXT_ACTION=` as the sole prompt-side routing directive after normalization; keep `.completed/step-3-terminal` and `.completed/step-3` double-gating in `skills/design/SKILL.md`.

NEXT_ACTION map: `complete`→`step3b`; `cap-hit`/`panel-failed`/`tally-error`/`degraded-empty-collector`→`step3b-bypass`; `main-agent-vote-required`→`mav`; `main-agent-apply-required`/`per-round-approval-required`→`gate-b`; `postplan-operator-required`→`postplan-operator`; `postplan-failed`→`final-summary:failed-postplan`; `panel-init-failed`→`final-summary:failed-judge-panel`; `zero-findings-degraded-panel` (no loop envelope)→`step3b`; MAV retally tally-error→`step3b-bypass`.

Special rules: suppress `NEXT_ACTION` on `persist_retally_step3_env` when `retally_status=ok` (mid-loop resume must not see terminal route); `NEXT_ACTION` precedes raw status in all post-loop prompt-side routing; `STEP3_REVIEW_LOOP_STATUS` remains authoritative for mid-loop resume flag selection.

## Acceptance

- `NEXT_ACTION=` emitted by `normalize-status` stdout and persisted in `.step3-review-result.env` for all terminal status paths.
- SKILL.md "Post-loop branch matrix" replaced with compact `NEXT_ACTION` routing table; sentinel double-gating prose unchanged.
- "Legacy single-round `LOOP_STATUS` mapping" section removed; `--mode single` references retired from SKILL.md and approval-gates.md.
- `test-step3-review-cap.sh` and `test-step3-orchestrator-fence.sh` harness pins updated before prose deletion.
- `python3 -m pytest python/test_plan_review.py` passes with `NEXT_ACTION` coverage; `make lint` and `make py-lint` pass.

diff_lines: 680

## Test plan
(no test plan section in plan-file)
