### [rejected] FINDING_13

**Rejected subtype:** dismissed (0 YES)

### FINDING_13: Validator env allowlist omits SITE and other wrapper keys
- **Reviewer(s)**: dyn-env-rehydrate-output.txt
- **Severity**: important
- **Concern**: `_VALIDATOR_ENV_ALLOWLIST` omits `SITE` (and other wrapper keys Bash got via full `source`). `SITE` is usually passed as `--site` on the fence, but session-env-only keys are silently dropped on read. Escalation site tokens and Step 5c default target selection can mis-route if `SITE` is not also present in the parent process environment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-env-rehydrate-output.txt: Align validator allowlist/defaults with the design wrapper surface (`SITE`, `MODE`, `SKIP_VALIDATE`, `LARCH_CLAUDE_PLUGIN_ROOT`, router flags as needed), or reuse `_SESSION_ENV_ALLOWLIST` from `design_lifecycle.py` instead of maintaining a narrower duplicate list.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_2: Fatal postplan paths print emit stdout twice
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-postplan-rc-output.txt
- **Severity**: important
- **Concern**: On fatal postplan arms (`emit` rc `1`, `2`, or other unexpected rc), `_shared_step2b_postplan_body` prints captured emit stdout via `_print_text(captured)`, then `step2b_postplan_main` / `step2b_drafter_main` prints `result.stdout_lines` again (same buffer). Retired Bash printed emit output once. Duplicated `POSTPLAN_EMIT`/validation KV lines pollute operator output and can confuse consumers (including `design-step35-settle.sh`). Fatal paths also emit no `POSTPLAN_RC=` rows (Bash parity gap), compounding parse ambiguity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Print captured emit output exactly once on fatal arms.
  - From cursor-specialist-edge-cases-output.txt: Print captured emit output only once on fatal arms.
  - From dyn-postplan-rc-output.txt: Print fatal emit stdout in only one layer. Either drop `_print_text(captured)` from the fatal branch in `_shared_step2b_postplan_body` and let callers print `stdout_lines`, or stop re-printing in `step2b_postplan_main` / `step2b_drafter_main` when `result.status == "fatal"`.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_7: review_core ignores failed collect-findings
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `review_core` ignores non-zero `collect-findings` results and continues with default or stale KVs. If agent collect-results times out, collect-findings returns non-zero without fresh `FINDINGS_COUNT`, but review_core can emit zero-findings or stale results.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Check `collect_result.returncode` and fail the round before reading collect KVs.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_8: Missing dirty-tree sidecars treated as clean
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Missing dirty-tree sidecars are treated as clean. A reviewer output without a `.dirty-tree` proof reports `DIRTY_DETECTED=false`, unlike the shell path that failed closed on missing or non-clean sidecars.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Mark dirty unless each sidecar exists and contains `STATUS=clean`.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

