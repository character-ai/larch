## Acceptance

- `scripts/hook-bg-poll-guard.sh` releases the `design-step3-review` poll guard on `.completed/step-3-terminal` (written only after the loop persists the result envelope in the current wrapper pass), not on the early `.completed/step-3` milestone.
- A single non-sleeping foreground sentinel probe (`[ -f … ]` / `test -f …`, optional leading `DESIGN_TMPDIR=<abs>;`, optional `&& echo … || echo …` echo-only tail) targeting `.completed/step-3-terminal`, `.completed/step-5c-terminal`, or `.completed/step-final-summary` is allowed past the guard even when the sentinel file is absent (the WAIT case).
- Progress/result-artifact polling (`.step3-review-result.env`, `.design-publish-result.env`, task outputs, `plan-review/`), sleep loops, watcher loops, non-terminal `.completed/step-3` / `.completed/step-5c` probes, and symlinked sentinels remain denied while a marker is live.
- Stale `.completed/step-3-terminal` and `.step3-terminal-persisted-this-run` are cleared before every `design-step3-review.sh` launch and on Step 3 re-entry / auto-continuation.
- `python/plan_review.py` `_LEGACY_ASSETS` blobs for `review-design-step3-loop.sh` and `design-step3-state.sh` are regenerated from the edited live scripts; the live/embedded parity tests (`test_embedded_review_design_step3_loop_matches_live_script`, `test_embedded_design_step3_state_matches_live_script`) pass.
- `skills/design/SKILL.md`, `AGENTS.md`, and `skills/shared/orchestrator-never.md` document the foreground-probe recovery and no longer instruct the orchestrator to wait for a second `<task-notification>` after a premature one; `scripts/test-implement-anti-polling-rule.sh` pins are updated.
- `bash scripts/test-hook-bg-poll-guard.sh`, `make test-hook-bg-poll-guard`, `bash scripts/test-implement-anti-polling-rule.sh`, the Step 3 harnesses, and `make lint` all pass.
- The harness-level premature-notification root cause is explicitly NOT claimed as fixed.
