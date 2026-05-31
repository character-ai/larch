## Decision 1: Streak machinery
- **Question**: Relax the streak to one round, or remove the streak machinery entirely?
- **Resolution**: Remove the streak machinery entirely. Converge when a single non-degraded round has ≤5 accepted and 0 important accepted. Drop the `convergence_streak`/`CONVERGENCE_STREAK` variable, its `emit_kv`/`.step3-plan-review-result.env` emission, the `_next_convergence_streak` lookahead, and the `LOOP_REASON=streak` token (replace with a non-streak reason).
- **Source**: user

## Decision 2: Accepted threshold (de-config)
- **Question**: Bump the env-var default 3→5 keeping it configurable, or hardcode 5 and drop the env var (and flag)?
- **Resolution**: Hardcode the accepted bound to literal 5. Remove the `LARCH_DESIGN_CONVERGENCE_THRESHOLD` env var AND the `--convergence-threshold` CLI flag (plus its argv validation). SKILL.md Step 3 stops passing the flag; update the ~30 test call-sites and the `test-design-structure.sh` pin.
- **Source**: user

## Decision 3: No new configurability
- **Question**: Add a new env var for the (now single-round) streak count?
- **Resolution**: No. No new env var; the single-round / threshold-5 rule is hardcoded.
- **Source**: user

## Decision 4: Scope — both review loops
- **Question**: Only /design's plan-review loop, or also /implement's code-review-and-fix loop?
- **Resolution**: Both. Apply the same relaxation (single non-degraded round with ≤5 accepted and 0 important; remove `--convergence-threshold` flag, hardcode 5) to `/design`'s `skills/design/scripts/plan-review-loop.sh` AND `/implement`'s `skills/review-and-fix/scripts/review-and-fix.sh`.
- **Source**: user

## Decision 5: Preserved invariants (codebase findings)
- **Question**: What existing behavior must not change?
- **Resolution**: The "0 important accepted" gate exists in both loops (`_count_important_findings` in plan-review-loop.sh; `important_findings_present`/`important_scan_abort` in review-and-fix.sh) and is PRESERVED. The hard round cap (`LARCH_DESIGN_ROUND_CAP` / `--round-cap` and review-and-fix's `--round-cap`) is a separate concern and stays untouched. The plan-review-loop zero-findings convergence path (`ACCEPTED_COUNT==0` → converged) is independent of the streak/threshold and stays. review-and-fix's `convergence_candidate_status` allowlist and the important-scan-abort (rc=2) error path stay.
- **Source**: codebase
