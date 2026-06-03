## Decision 1: Call-site migration scope (prompt-side re-emit sites)
- **Question**: Migrate only the initial Step 2b post-plan fences, or also the other prompt-side `ACTION=EMIT_PLAN` re-emit sites (Gate A re-entry, Gate B, discussion-round2)?
- **Resolution**: Migrate the initial Step 2b fences AND the three prompt-side re-emit sites (Gate A re-entry / "Shared post-apply pipeline", Gate B post-apply, discussion-round2 sub-round) onto the new driver. Requirement: the driver MUST support suppressing the HARD `plan.txt-original` snapshot — that snapshot fires only at the initial Step 2b call; re-emit sites suppress it. Re-emit sites keep their existing pre-EMIT dedup pass (`gate-b-dedup-plan.sh --snapshot-trailers` / `--dedup`) OUTSIDE the driver (dedup mutates `plan.txt` before `diff-lines.txt` is recomputed).
- **Source**: user

## Decision 2: Loop-internal EMIT_PLAN sites are OUT of scope
- **Question**: Also fold `plan-review-loop.sh` and `revise-plan-with-waterfall.sh` (loop-internal EMIT_PLAN sites) onto the new driver?
- **Resolution**: No — leave them as-is. They already call `design-driver.sh` directly, carry bespoke `plan_backup`/restore + `LOOP_STATUS` rollback per step, and take no HARD snapshot; per-step semantics don't map onto a combined-status driver and folding them risks regressing the multi-round convergence loop. Out of scope for #3247 (a candidate for a future #3133 extraction).
- **Source**: user

## Decision 3: Hard constraints to preserve (machine-output contract + control boundary)
- **Question**: What behavior must the extraction preserve?
- **Resolution**: (a) Combined machine output the orchestrator parses: `EMIT_PLAN_STATUS`, a snapshot status, `VALIDATE_STATUS` + `VALIDATE_DEFECT_COUNT` / `VALIDATE_SKIPPED_COUNT` / `VALIDATE_UNSAFE_TOKEN_COUNT` / `VALIDATE_LOG_FILE`. (b) `defects-found` is NOT a script failure — surfaced as a status the orchestrator gates on. (c) Driver STOPS before the plan-command-validator-defects `AskUserQuestion` (shared Fix-and-retry / Override / Cancel body) and before Step 2b.5. (d) `review_budget=quick` skips the validator entirely. (e) `EMIT_PLAN_STATUS=missing-diff-lines` / non-zero EMIT stays a hard failure the orchestrator repairs (`plan.txt`). (f) The HARD snapshot still aborts the step on snapshot failure at the initial Step 2b call. (g) No duplication — driver calls `design-driver.sh` (EMIT_PLAN), `snapshot-plan-round.sh write-original`, and `invoke-plan-validator.sh` internally.
- **Source**: codebase (issue body + existing SKILL.md Step 2b fences)

## Decision 4: Repo conventions (sibling artifacts + reuse)
- **Question**: What supporting artifacts must ship?
- **Resolution**: Follow the umbrella #3133 sibling-driver pattern: new `skills/design/scripts/design-postplan-emit.sh` (reusing `lib-phase-driver.sh`: `phase_driver_resolve_plugin_root`, `phase_driver_write_result_env`, `larch_quiet_init`, `emit_kv`; exit 2=config, 1=op-fail, 0=ok; result-env + stdout-KV dual emit) + sibling `design-postplan-emit.md` contract + offline harness `test-design-postplan-emit.sh` (+ `.md` stub) + Makefile target + `scripts/test-design-structure.sh` fence/anchor pin updates. Grep `docs/`, `skills/**`, `README.md` for stale Step 2b fence pointers (drift-prone-prose rule).
- **Source**: codebase (.claude/rules + sibling drivers `design-publish.sh` / `design-init-runparams.sh`)
