### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: No harness for invalid `LARCH_FAILED_AGENT_STDERR_TAIL_LINES` env fallback
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Non-numeric `LARCH_FAILED_AGENT_STDERR_TAIL_LINES` fallback to 30 lines is untested; under `set -u` or bad env, tail behavior could regress to empty/disabled tails without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Assert `LARCH_FAILED_AGENT_STDERR_TAIL_LINES=abc` yields 30 lines from a 40-line source.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: Harness does not assert `.stderr-tail` written before `.done` on launcher failure
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `test-launch-claude-subprocess.sh` does not verify ordering between `${fail_out}.stderr-tail` and `${fail_out}.done`; reordering could let the collector observe `.done` without a tail sidecar.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add mtime/ordering assertion between `${fail_out}.stderr-tail` and `${fail_out}.done`.
  - From cursor-specialist-plan-fidelity-output.txt: Add ordering assertion or stub-based intermediate check


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: Plan-review collector stderr tee lacks behavioral tail visibility test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `test-plan-review-loop.sh` pins golden layout only; degraded `/design` collector failures might tee to `plan-review-collector.stderr` without fenced tails reaching orchestrator FD 2/4.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Stub a failed collect with `.stderr-tail` sidecars and assert tee/captured stderr contains the fenced tail.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: No test that `.stderr-tail` artifacts are published in design run logs
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Without a publish harness case, regressions that re-exclude `*.stderr-tail` from cloned log trees would silently remove run-log recoverability.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add one publish harness case expecting `.stderr-tail` in the cloned log tree.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: Published `*.stderr-tail` in `larch-logs/` without gitleaks backstop
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Publishable `.stderr-tail` artifacts can land in `larch-logs/` where gitleaks does not scan; `redact-secrets` has known non-coverage, so opaque secrets in stderr could be committed in public run logs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Exclude *.stderr-tail from publish or add publish-time re-redaction; treat larch-logs as sensitive regardless of redaction.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: Success-path collector stderr replay/fanout skips `redact-secrets.sh`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: On `collector_rc=0`, `replay_collector_failed_stderr_tails` / fanout may replay already-written `.stderr-tail` files using only `sanitize_diagnostic_line`, not `redact-secrets.sh` / `redact-tmpdir-paths.sh`, so tampered or stale unredacted tails in `REVIEW_TMPDIR` could reach FD 2.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Pipe replay/fanout through redact-tmpdir-paths.sh and redact-secrets.sh for defense in depth.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_24

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_24: `hook-anti-read-poll.sh` `||`/`&&` segment splitting ignores shell precedence
- **Reviewer(s)**: dyn-bash-hook-correctness-output.txt
- **Severity**: important
- **Concern**: Heuristic splitting on `;`, `&&`, `||` left-to-right without Bash precedence can attach poll detection to the wrong segment or miss `tasks/…output` reads in compound one-liners.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-hook-correctness-output.txt: Prefer detecting poll only on segments that both contain a read verb and a `tasks/<id>.output` token after strip (already mostly true), and add harness cases for mixed `||`/`&&` chains that match real orchestrator patterns; long term, only split on `;` (statement boundaries) unless you implement precedence-aware parsing.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Triplicate fenced-tail emit logic across lib, collector, collect-findings
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Fenced stderr-tail emit loops are duplicated in `lib-failed-agent-stderr-tail.sh`, `collect-agent-results.sh`, and `collect-findings.sh`. Sanitization, fence format, caps, and redaction can drift; future changes require triple maintenance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add shared lib emit helper (quiet vs raw); delete duplicate loops in collector and collect-findings.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: Collector §3.8 dedup/resolve helpers inlined in large collector script
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: §3.8 stderr-tail dedup and resolve helpers live inline in a ~1580-line `collect-agent-results.sh`, mixing stderr-tail concerns with retry/validation logic and making the behavior harder to test and reason about.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract §3.8 helpers to lib-failed-agent-stderr-tail.sh or a collector-specific sourced module.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: Extra redacted stdout tail block on FAILED in `run-external-agent.sh`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Beyond planned additive stderr surfacing, FAILED handling may render an extra redacted stdout tail from `OUTPUT_FILE`, producing duplicate or confusing failure blocks (stdout snippet plus stderr tail) not in acceptance criteria.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Remove extra render on OUTPUT_FILE unless explicitly desired; keep stderr-tail sidecar + emit only.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: Aggressive stderr-tail signature normalization may over-dedup distinct failures
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Replacing all `[0-9]+` runs with `#` in tail signatures can collapse materially different failures (line numbers, HTTP status, exit codes) into one emitted tail plus suppression lines, hiding separate root causes in one batch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Tighten normalization or exempt certain STATUS values from signature dedup.
  - From cursor-specialist-edge-cases-output.txt: Tighten normalization or dedup on a stable error-class prefix instead of all digits.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

