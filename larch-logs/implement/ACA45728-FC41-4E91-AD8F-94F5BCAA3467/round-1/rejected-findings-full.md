### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: Plan-review collector stderr bypasses tail redaction pipeline
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Collector stderr is teed raw to FD 2/4 without the failed-agent tail redaction pipeline. On collect failure after a panel reviewer prints tokens or tmpdir paths to stderr, chat and `plan-review-collector.stderr` may receive unredacted content while implement lanes use lib-redacted tails.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Route collector stderr through render_failed_agent_stderr_tail / §3.8-style emission on failure, or document this as an intentionally unredacted design diagnostic channel.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: `run_codex` tail write lacks cursor-style absent-file guard
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `run_codex` unconditionally calls `write_failed_agent_stderr_tail` without checking for an existing `${run_dir}/codex.log.stderr-tail`. If `run-external-agent` already wrote a tail, a weak overwrite from the wrapper log is possible (low risk with current `--stderr-sink`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Mirror run_cursor: only write_failed_agent_stderr_tail when ${run_dir}/codex.log.stderr-tail is absent.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: Implementer agent-failure tests omit redaction bound assertions
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Agent-failure harness cases do not assert line/byte caps or redaction bounds required by plan wording. Unbounded or unredacted tail content could regress in launcher write paths while probe greps still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Port line/byte-cap assertions from test-lib-failed-agent-stderr-tail.sh or document lib-only coverage in harness contract.
  - From cursor-specialist-plan-fidelity-output.txt: Add line/byte bound assertions or document reliance on test-lib-failed-agent-stderr-tail in the case header.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: Lint-fix-loop harness fixture copy list can drift from sources
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The growing list of files copied into lint-fix-loop harness fixtures can drift from `lint-fix-loop.sh` sources. A new sourced file without a harness copy can yield false-green offline tests or false-red CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Document sync requirement in test-lint-fix-loop.md or add pre-case check that all sourced files are copied.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Duplicated STDERR_TAIL_PATH / CODER_LOG_FILE stem selection
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Stem-resolution logic for `STDERR_TAIL_PATH` and `CODER_LOG_FILE` is duplicated between `scripts/ship-pr.sh` and `skills/review-and-fix/scripts/review-implement-step5-loop.sh`. Future KV or ordering changes can desync ship-pr and Step 5 surfacing behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract one shared stem-resolution helper used by both.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

