### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: phase_driver_read_result_env unused; duplicated env parsing in driver
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `phase_driver_read_result_env` in `lib-phase-driver.sh` is unused; the driver duplicates allowlisted parse loops and a dead `_allow` array, inviting future drift between lib helper and inline copies.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Use phase_driver_read_result_env or one helper for inner env and stdout fallback


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: Stale `.step3-review-result.env` on driver re-entry
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: The driver clears inner `.step3-plan-review-result.env` before the loop but not `.step3-review-result.env`. Re-entry after a prior complete run can leave stale `LOOP_STATUS=complete` if the process crashes before the final write; the orchestrator may source the stale file and skip stdout fallback, entering Gate B incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: rm -f normalized result env at driver start or write pending sentinel before loop


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: `.step3-review-cap.env` shell-sourced instead of allowlisted parse
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Cap state is written then `source`d without symlink refusal, unlike the documented result-env trust model for `.step3-review-result.env`. Same-UID tampering between write and source could execute arbitrary shell.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Refuse symlink targets before cat/source, or eliminate sourcing and keep cap state in process-local variables.
  - From cursor-specialist-edge-cases-output.txt: Replace source with allowlisted KV read consistent with SECURITY.md and SKILL.md orchestrator fence


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: `RUN_STEP3_PLAN_REVIEW_LOOP_SH` runs arbitrary executable path
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: The driver invokes any executable path from the environment with only an `-x` check. An env-injecting attacker in a shared design session could substitute a malicious binary while SKILL.md still routes through normal Step 3 gates.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Document tests-only; optionally gate on LARCH_TEST_MODE or require the path to resolve under PLUGIN_ROOT.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: No integration coverage for SKILL → run-step3-review → plan-review-loop
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Wiring mistakes in SKILL fence argv or result-env handoff may pass unit tests but fail full Step 3 flow; plan test strategy calls for broader coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Extend integration harness or document explicit rationale.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_23: Cap-reached harness does not assert plan-review-loop was skipped
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Cap-reached test may pass even if the loop stub is invoked unless the stub fails or touches a marker.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Have stub touch a marker file or fail with exit 97 when invoked.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_25

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_25: Unused orchestrator allowlist keys blur driver/orchestrator split
- **Reviewer(s)**: dyn-driver-orchestrator-boundary-output.txt
- **Severity**: latent
- **Concern**: SKILL loads `STEP3_REVIEW_ROUND_NUM` and `REVIEW_ROUND_COUNT` from the normalized env but no post-loop branch consumes them; round cap/persist/rollback live entirely in `run-step3-review.sh`, widening orchestrator surface without LLM-layer use.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-driver-orchestrator-boundary-output.txt: Drop the unused keys from the orchestrator allowlist (keep them driver-internal), or add a one-line contract note that they are diagnostic-only if retained for logging.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Orchestrator non-zero rc override can clobber file-resident LOOP_STATUS
- **Reviewer(s)**: dyn-driver-orchestrator-boundary-output.txt
- **Severity**: important
- **Concern**: After sourcing `.step3-review-result.env`, the fence still forces `LOOP_STATUS=panel-failed` on any non-zero driver rc (except `main-agent-vote-required`), contradicting the file-first post-loop matrix. Today exit `1` is mostly cursor failure with matching env, but any future non-zero exit after a successful `phase_driver_write_result_env` (or a `set -e` abort before `exit 0`) could turn `cap-reached` / `converged` / `complete` into `panel-failed` and mis-route Gate B / Step 3b.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-driver-orchestrator-boundary-output.txt: Apply the rc override only when `LOOP_STATUS` is still empty after file + stdout ingestion, or only for argv failures (`rc=2`) / missing result env; keep trusting the normalized `.step3-review-result.env` when it was sourced successfully.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: Orchestrator no longer validates LOOP_STATUS against full allow-list
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: After the driver returns, the SKILL fence only normalizes empty `LOOP_STATUS` to `panel-failed`. A tampered or corrupted `.step3-review-result.env` with an invalid status could reach the branch matrix and skip expected gates.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Re-apply allow-list normalization in the SKILL fence or prefer driver stdout when file and stdout disagree.
  - From cursor-specialist-plan-fidelity-output.txt: Re-add allow-list validation in SKILL after sourcing or fail closed when the normalized env is malformed.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

