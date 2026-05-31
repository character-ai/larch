### FINDING_15: [OUT_OF_SCOPE] Step 3.6 does not consume driver-persisted `ROUND_NUM`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Step 3.6 re-reads `ROUND_CURSOR` from `snapshot-plan-round.sh` instead of sourcing `ROUND_NUM` from `.step3-review-result.env` written by the new driver. Cross-fence shell locals were already unreliable; the driver persists `ROUND_NUM` but Step 3.6 does not consume it (pre-existing gap).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_16: [OUT_OF_SCOPE] `phase_driver_read_result_env` exported but unused by first consumer
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-orchestrator-bridge-contract-output.txt
- **Severity**: nit
- **Concern**: `lib-phase-driver.sh:59-77` defines `phase_driver_read_result_env` (tested) but `run-step3-review.sh` still uses inline `case` parsing and a dead `_allow` array. Future drivers may copy the inline pattern and diverge from the shared primitive.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-orchestrator-bridge-contract-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


### FINDING_17: [OUT_OF_SCOPE] `test-lib-phase-driver.sh` uses `TMPDIR` not larch sessions cache
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `test-lib-phase-driver.sh` uses `TMPDIR` instead of the `~/.cache/larch/sessions` convention used by sibling harnesses, diverging from repo session tmp roots.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated


### FINDING_18: [OUT_OF_SCOPE] Newline-bearing KV values can expand result-env lines
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Newline-bearing KV values can produce extra result-env lines when persisted; spoofed inner env can set multiple orchestrator variables via one logical value (pre-existing).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_19: [OUT_OF_SCOPE] `--design-tmpdir` not rooted under larch session directory
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `--design-tmpdir` is not validated as rooted under a larch session directory; a malicious or mistaken argument can enable read/write outside intended session artifacts (pre-existing trust model).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_20: [OUT_OF_SCOPE] `approval-gates.md` dual result-env references out of sync
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-orchestrator-bridge-contract-output.txt
- **Severity**: latent
- **Concern**: Gate B instructions still normatively reference `.step3-plan-review-result.env` while the Step 3 branch matrix cites normalized `.step3-review-result.env`. Both can exist after a successful run; doc drift risks inconsistent handoff guidance, not a missing bridge key for gate dispatch in this PR.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-orchestrator-bridge-contract-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_21: [OUT_OF_SCOPE] SIMPLE tier cap vs `LARCH_DESIGN_ROUND_CAP` can disagree
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: SIMPLE tier may hit review-round cap at 3 while the loop uses env round-cap 5; tier cap and `LARCH_DESIGN_ROUND_CAP` can disagree (pre-existing policy).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated


### FINDING_22: [OUT_OF_SCOPE] Dropped inner keys not copied to normalized result env (intentional)
- **Reviewer(s)**: dyn-orchestrator-bridge-contract-output.txt
- **Severity**: latent
- **Concern**: The driver parses inner keys (`REASON`, `REVISE_STATUS`, `CONVERGENCE_STREAK`, `COLLECT_*`, `VOTER_1_PARSE_RATE_STATUS`) for loop handoff but does not copy them into `.step3-review-result.env`. This matches the documented normalized surface and is not a silent orchestrator regression: `SKILL.md` does not reference those shell variables after the bridge; Gate B reads inner/`round-summary.env` paths directly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-orchestrator-bridge-contract-output.txt: Address the concern above.

---

**Merge notes (for voters, not machine output):**

- Input **FINDING_29** (allowlist parity confirmation) and **FINDING_32** (branch commit list) were treated as non-actionable attestations and omitted.
- **FINDING_7** (exit-2 test gap) was kept separate from **FINDING_3** (orchestrator stale-env behavior) because fixes differ (harness vs fence gating).
- **FINDING_30** was subsumed into **FINDING_1** (in-scope) and **FINDING_16** (OOS unused-helper angle).

Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected


