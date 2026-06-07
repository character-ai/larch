### FINDING_1: Auto-continuation expands cross-vendor security review exposure
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Multi-round auto-continuation can resend Gate-B-revised plans, including security finding details, to external reviewers without per-round operator consent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_2: Cumulative accepted findings may publish security-sensitive prose
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `accepted-plan-findings-all.md` accumulates full in-scope finding blocks and is published in logs without filtering security-tagged accepted findings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_3: Concern-text severity fallback can trigger spurious continuation
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Broad regex fallback over finding prose can treat incidental “high” / “critical” wording as important severity and force unnecessary external review rounds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] SECURITY.md still describes Step 3 as single-pass
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: SECURITY.md may understate the new heuristic multi-round behavior and its trust-boundary implications.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_5: Cumulative accepted-findings writes follow symlinks
- **Reviewer(s)**: codex-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Writes to symlinked `accepted-plan-findings-all.md` can overwrite arbitrary local files from the design tmpdir.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-security-output.txt: Address the concern above.

### FINDING_6: Auto-continuation leaves Step 3 sentinel state unsafe for pause/resume
- **Reviewer(s)**: codex-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-state-machine-output.txt
- **Severity**: important
- **Concern**: Follow-up Step 3 rounds can run while `.completed/step-3` remains set and `.completed/step-3.5` absent, causing pause/resume to jump to Gate B and skip an unfinished review panel or reuse stale artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-state-machine-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] Single Important finding triggers continuation despite implement threshold
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-state-machine-output.txt, dyn-artifact-state-output.txt
- **Severity**: important
- **Concern**: `/design` continues on any important accepted finding, while the intended `/implement` symmetry requires at least two important findings or other substantial-change signals.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, dyn-state-machine-output.txt, dyn-artifact-state-output.txt: Address the concern above.

### FINDING_8: Structural/HARD continuation predicate is too broad
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-state-machine-output.txt
- **Severity**: important
- **Concern**: HARD tier, plan size, or diff size can force round-2 continuation even for nit-only or otherwise clean rounds, making small-clean convergence unreachable in common cases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, dyn-state-machine-output.txt: Address the concern above.

### FINDING_9: Zero-findings Gate B prose bypasses continuation check
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-state-machine-output.txt
- **Severity**: important
- **Concern**: Documentation still routes zero-findings Gate B directly to Step 3b, which can skip the continuation helper for degraded zero-finding panels.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-state-machine-output.txt: Address the concern above.

### FINDING_10: Continuation lacks implement-like post-fix or structural-size signals
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `/design` can stop after many latent findings because it has no equivalent to `/implement`’s post-fix-count or structural-LOC substantial-round predicates.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] Cumulative accepted findings can duplicate logical findings and inflate counts
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-state-machine-output.txt, dyn-artifact-state-output.txt, dyn-bash-portability-output.txt
- **Severity**: latent
- **Concern**: In-scope cumulative accumulation concatenates blocks without consistent deduplication, so repeated logical findings across rounds can inflate final summary accepted counts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, dyn-state-machine-output.txt, dyn-artifact-state-output.txt, dyn-bash-portability-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] Multi-round integration and pause/resume coverage is missing
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-state-machine-output.txt, dyn-artifact-state-output.txt
- **Severity**: nit
- **Concern**: Existing harnesses do not exercise a full Step 3 → Gate B → continuation → Step 3 loop or pause-during-auto-continuation behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, dyn-state-machine-output.txt, dyn-artifact-state-output.txt: Address the concern above.

### FINDING_13: Continuation helper invocation uses stale approve_requested variable
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `SKILL.md` references `approve_requested` even though only `_approve_requested` is set in the relevant shell scope, so the continuation helper can receive an empty/unbound argument and fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.

### FINDING_14: Gate-B-settled prose still routes directly to Step 3b
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Stale SKILL and approval-gate directions can skip the new continuation check after Gate B applies accepted findings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.

### FINDING_15: Automatic continuation deletes prior round artifacts
- **Reviewer(s)**: codex-specialist-correctness-output.txt, dyn-artifact-state-output.txt
- **Severity**: latent
- **Concern**: `run-step3-review.sh` removes prior `plan-review/round-*` directories on each Step 3 entry, destroying earlier automatic-round ballots, summaries, and classification artifacts while cumulative session-root files persist.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, dyn-artifact-state-output.txt: Address the concern above.

### FINDING_16: MainAgent-required rounds can accumulate tentative accepted findings
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Findings later rejected or errored by MainAgent can remain in `accepted-plan-findings-all.md` and be reported as accepted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_17: Final summary can count findings explicitly skipped at Gate B
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `render-final-summary.sh` prefers cumulative accepted findings even after one-by-one Gate B approval skips, so skipped findings can remain in the accepted count.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_18: Continuation predicate branches lack targeted coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Small-clean convergence, non-nit continuation, and structural/HARD continuation branches lack harness coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_19: Cumulative accepted append and restore behavior lacks tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `_accumulate_round_accepted_all` and panel-failed/tally-error restore paths are not covered by behavioral tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_20: Persist-retally cumulative merge tests are not wired into relevant checks
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-bash-portability-output.txt
- **Severity**: important
- **Concern**: New `persist-retally-step3-env` merge behavior has test coverage but edits to the script are not mapped through `relevant-checks.sh` / make shard routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-bash-portability-output.txt: Address the concern above.

### FINDING_21: Direct-review-entry cleanup assertion is incomplete
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Tests do not assert that `accepted-plan-findings-all.md` is removed during direct Step 3 review re-entry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_22: Continuation tier resolution uses stale workflow_path precedence
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The continuation helper can prefer `workflow_path` over canonical `design_classification` and fail to default invalid/missing classification to HARD.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Address the concern above.

### FINDING_23: Gate-B postapply-ready markers can accumulate across automatic rounds
- **Reviewer(s)**: dyn-state-machine-output.txt
- **Severity**: latent
- **Concern**: Automatic Step 3 continuation does not clear `.gate-b-postapply-ready-*`, leaving pause/resume idempotency dependent on correctly bound round state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-machine-output.txt: Address the concern above.

### FINDING_24: Degraded zero-finding panels can burn the review cap
- **Reviewer(s)**: dyn-state-machine-output.txt, dyn-artifact-state-output.txt
- **Severity**: important
- **Concern**: `DEGRADED_PANEL=1` alone forces continuation even with zero accepted findings, potentially consuming multiple external review rounds without applied fixes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-machine-output.txt, dyn-artifact-state-output.txt: Address the concern above.

### FINDING_25: Manual re-entry leaves prior OOS accepted findings
- **Reviewer(s)**: dyn-artifact-state-output.txt
- **Severity**: latent
- **Concern**: Direct Step 3 re-entry clears cumulative in-scope accepted findings but leaves `oos-accepted-design.md` and its previous snapshot, so stale OOS findings can survive a fresh manual panel run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-artifact-state-output.txt: Address the concern above.

### FINDING_26: Tally-error rollback leaves accepted artifacts inconsistent
- **Reviewer(s)**: dyn-artifact-state-output.txt
- **Severity**: latent
- **Concern**: The `tally-error` path restores cumulative accepted findings but can leave `accepted-plan-findings.md` and `ACCEPTED_COUNT` reflecting partial failed tally output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-artifact-state-output.txt: Address the concern above.

### FINDING_27: plan-review-continuation python3 failure path is brittle
- **Reviewer(s)**: dyn-bash-portability-output.txt
- **Severity**: latent
- **Concern**: `plan-review-continuation.sh` relies on `python3` inside command substitution under `set -euo pipefail` without availability checks, diagnostics, or safe fallback KVs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-portability-output.txt: Address the concern above.

### FINDING_28: persist-retally python3 merge path lacks error handling
- **Reviewer(s)**: dyn-bash-portability-output.txt
- **Severity**: latent
- **Concern**: `_merge_retally_accepted_all` runs inline Python unconditionally, so Python absence or failure can abort the persist step and leave Step 3 env/cumulative state stale.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-portability-output.txt: Address the concern above.

### FINDING_29: [OUT_OF_SCOPE] render-final-summary array expansion lacks defensive Bash 3.2 idiom
- **Reviewer(s)**: dyn-bash-portability-output.txt
- **Severity**: nit
- **Concern**: The new array expansion does not use the safe-empty idiom, though an existing `-s` guard makes this a minor defensive-style gap rather than a demonstrated regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-portability-output.txt: Address the concern above.

### FINDING_30: [OUT_OF_SCOPE] Pre-existing dependency patterns noted as scope context
- **Reviewer(s)**: dyn-bash-portability-output.txt
- **Severity**: nit
- **Concern**: Existing `python3`, `jq`, and process-substitution usage follows established repository patterns; this was noted as review scope context rather than a new branch regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-portability-output.txt: Address the concern above.
