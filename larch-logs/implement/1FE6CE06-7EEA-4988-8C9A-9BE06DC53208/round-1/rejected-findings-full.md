### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: PR head is not re-verified immediately before admin merge
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-gh-ci-gate-output.txt
- **Severity**: important
- **Concern**: `PUSH_HEAD_SHA` / `headRefOid` equality is checked to exit registration, but not rechecked after `--watch` and before `gh pr merge --admin`, leaving a window where a moved disposable branch could merge content not independently tied to the originally pushed SHA.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, dyn-gh-ci-gate-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: Registration timeout message does not match actual wall-clock behavior
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-bash-contract-output.txt, dyn-gh-ci-gate-output.txt
- **Severity**: latent
- **Concern**: The registration loop is probe-count bounded while `gh pr view` retries can add backoff per probe, so elapsed wall time can exceed the advertised `${REG_TIMEOUT}s` diagnostic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-bash-contract-output.txt, dyn-gh-ci-gate-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: Registration is not rechecked immediately before watch
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Checks could disappear between the final successful registration probe and `gh pr checks --watch`, recreating a narrow no-checks-reported watch failure window.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: Registration temp files are not covered by cleanup trap
- **Reviewer(s)**: dyn-bash-contract-output.txt
- **Severity**: latent
- **Concern**: `reg_checks_err_file` and `reg_view_fail_file` are removed after the loop but not in `wt_cleanup`, so an early second-`mktemp` failure can leak the first temp file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-contract-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: Registration gate logic is inlined in a long script block
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: The registration wait, headRefOid binding, and merge result assignment are embedded directly in `scripts/design-log-publish.sh`, making future edits harder to review and increasing duplication risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: Probe counter can stay at one when `GH_STUB_LOG` is unset
- **Reviewer(s)**: dyn-harness-fidelity-output.txt
- **Severity**: latent
- **Concern**: JSON probe numbering only persists when `GH_STUB_LOG` or `GH_STUB_CHECKS_JSON_COUNT_FILE` is set, so pause-reuse paths without logs cannot validate multi-probe behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-fidelity-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: `merge_rc` lacks a defensive initializer
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `merge_rc` is used under `set -u`; current paths assign it, but a future refactor could trigger an unbound-variable abort instead of a clean `PUBLISH_OK=false`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: Success-path harnesses do not consistently assert registration probes before watch
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-harness-fidelity-output.txt
- **Severity**: latent
- **Concern**: Happy-path and stale-head-success tests can pass without proving `gh pr checks --json` registration probes occurred before `gh pr checks --watch --fail-fast`, so regressions that skip the completion watch could be missed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-harness-fidelity-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: Persistent `gh pr view` failure during registration is untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The harness does not cover non-zero `gh pr view` during registration when checks JSON is non-empty, leaving the fail-closed registration-timeout behavior unverified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

