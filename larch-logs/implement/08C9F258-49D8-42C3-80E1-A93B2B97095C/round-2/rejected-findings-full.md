### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: Codex launcher does not scan symlinks inside session tmpdir
- **Reviewer(s)**: dyn-codex-sandbox-symlink-output.txt
- **Severity**: latent
- **Concern**: Symlink rejection applies only to the immediate parent directory argument, not to entries inside `codex-step2-out/`. If an attacker can create a symlink under that directory before Codex runs (writable session cache), `--add-dir "$SESSION_TMPDIR"` may still follow it depending on Codex sandbox semantics, potentially allowing writes outside the intended subdir while the parent passes `-L`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-codex-sandbox-symlink-output.txt: After `mkdir -p` in `step2-implement.sh`, optionally scan `codex-step2-out` for symlinks before launch, or document and enforce that only the dispatcher creates that tree and session tmpdirs are user-private with restrictive permissions.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: `run_evaluate_failure` grew into deep single-function control flow
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `run_evaluate_failure` grew into a deep single-function control-flow block. Harder to verify defer vs dispatch invariants and risks copy-paste drift on the next CI fix change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: `code_fix_attempted_on_ready_log` duplicated across many return sites
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `code_fix_attempted_on_ready_log` duplicated across many `FixResult` return sites. Easy to set the flag on one new return path and miss another, breaking Bash/Python parity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: No-blind-rerun test does not assert fix machinery ran
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Deterministic no-blind-rerun test does not assert fix machinery ran before stall. Acceptance requires code fix before retry; test only proves no `ci-rerun-failed.sh` and exit 4.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: Step 8 harness greps token presence not autonomous When-clause pairing
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Step 8 harness only greps `ci-fix-exhausted` presence, not autonomous When clause pairing. SKILL prose could mention token outside the autonomous When sentence; harness still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: Bash per-job-before-vendor vs Python vendor-before-per-job ordering
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Bash runs per-job local fixes before vendor; Python runs vendor waterfall before per-job inside `run_ci_fix`. Makes `bool(classified.fixable)` a poor parity stand-in for substantive attempts. Autonomous routing can diverge for the same CI failure shape across `LARCH_SHIP_PR_IMPL` modes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: Optional redundant `gh` call when transient retries at cap
- **Reviewer(s)**: dyn-bash-python-parity-output.txt
- **Severity**: nit
- **Concern**: When `transient_retries` is already at the cap, Bash skips the upfront `gh-run-logs.sh` call entirely; Python always calls `collect_failed_logs` before the gated rerun block. Does not change retry-vs-fix decisions—the rerun branch is skipped in both trees—but Python makes a redundant `gh` call.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-python-parity-output.txt: Wrap the Python upfront collect inside the same `transient_retries < max` guard to avoid a redundant `gh` call.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: Global write_stubs default may silently change unrelated fix-loop tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `write_stubs` now defaults `gh-run-logs` and `ci-failed-jobs` for every `make_repo`, replacing copied real `ci-failed-jobs.sh`. Unrelated fix-loop cases may change behavior (empty jobs, deterministic logs) without local overrides, causing silent regressions in `make test-ship-pr-fix-loop`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: Autonomous CI-fix expands prompt-injection reach after exhaustion
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `ci-fix-exhausted` now triggers autonomous main-agent CI-fix without `AskUserQuestion`, expanding write/commit/push cycles informed by redacted but untrusted CI logs. A compromised or malicious CI job prints instruction-like text; after in-script fix exhaustion the orchestrator autonomously edits the repo up to three times before user bail, amplifying prompt-injection reach versus stall-only behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

