### OOS_1: [OUT_OF_SCOPE] session_get not deduplicated with lib-phase-driver.sh
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `skills/implement/scripts/run-step2-dispatch.sh` duplicates `session_get` instead of using `lib-phase-driver.sh`; pre-existing implement stack, not this PR.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Consolidate when a run-step2 phase-driver lands under #3133


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### OOS_2: [OUT_OF_SCOPE] approval-gates.md still references inner result env
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Gate B prose still references `.step3-plan-review-result.env` while Step 3 primary handoff is `.step3-review-result.env`; dual-source drift for operators following approval-gates. Not introduced by this driver extract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: update approval-gates in a follow-up


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_3: [OUT_OF_SCOPE] phase_driver_read_result_env unused by first consumer
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Duplicated parsing logic only in `run-step3-review.sh`; no current runtime failure mode; defer wiring to lib helper.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Use lib in driver or defer until next driver lands
  - From cursor-specialist-edge-cases-output.txt: Wire driver to lib helper in a follow-up refactor


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_4: [OUT_OF_SCOPE] Plugin root resolution trusts session-env without attestation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `CLAUDE_PLUGIN_ROOT` and session-env can redirect `PLUGIN_ROOT` script invocations; predates this refactor; belongs in session-env hardening.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: belongs in a session-env hardening change


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### OOS_5: [OUT_OF_SCOPE] Collector stderr FIFO path lacks symlink checks
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: FIFO under `DESIGN_TMPDIR` created without symlink checks; symlink could redirect fifo I/O (DoS/misleading stderr). Follow existing DESIGN_TMPDIR symlink conventions elsewhere; not introduced here.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: follow existing DESIGN_TMPDIR symlink conventions used elsewhere in design scripts


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_6: [OUT_OF_SCOPE] Inner cap-reached block is redundant dead logic
- **Reviewer(s)**: dyn-shell-state-machine-output.txt
- **Severity**: nit
- **Concern**: Re-sourcing `$CAP_ENV` after the top-of-script write makes the inner `STEP3_REVIEW_CAP_REACHED=true` block at 147–150 unreachable when 99–116 succeeded; code-quality only, not a silent partial-write masker under `set -euo pipefail`.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### OOS_7: [OUT_OF_SCOPE] `_step3_prior_round_count` matches main parity
- **Reviewer(s)**: dyn-shell-state-machine-output.txt
- **Severity**: nit
- **Concern**: Initialization, numeric guard, and rollback at 265–266 match pre-refactor inline fence; corrupt `STEP3_REVIEW_ROUND_NUM` rollback edge case is latent and pre-existing.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_8: [OUT_OF_SCOPE] LOOP_STATUS allow-list doc drift in plan-review-loop.md
- **Reviewer(s)**: dyn-shell-state-machine-output.txt
- **Severity**: nit
- **Concern**: Driver regex includes `optional-trailer-dedup-loss` per removed SKILL inline list; `plan-review-loop.md:44` omits it though the loop emits it—pre-existing doc drift; driver aligns with implementation.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### OOS_9: [OUT_OF_SCOPE] Harness does not assert REVIEW_ROUND_COUNT on rollback via stdout/env
- **Reviewer(s)**: dyn-shell-state-machine-output.txt
- **Severity**: nit
- **Concern**: `test-run-step3-review.sh` checks file rollback for tally/degraded paths but not `REVIEW_ROUND_COUNT=` in stdout/`.step3-review-result.env` on rollback; file checks deemed sufficient for core contract.
- **Suggested revisions (informational for voters; coder decides)**:

Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

