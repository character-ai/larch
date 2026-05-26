### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: correctness: scripts/ship-pr.sh:1162-1168
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Breadcrumb publish failure inside larch-log commit is non-fatal at ship-pr pre-PR-create Pre-PR-create redaction failure: PR still created without committed breadcrumbs while raw streams sit in tmpdir Fail ship-pr step or add mandatory teardown commit on breadcrumb publish failure
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_12: correctness: scripts/ci-wait.sh:191-208
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Plan said larch_err for error-tier paths; code still uses larch_errf No functional regression on stream-unset harness; plan/doc mismatch only Align plan/docs or rename calls to larch_err if desired
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: risk-integration: scripts/test-breadcrumb-monitor.sh:261-286
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Test 7 does not assert poll-interval+1s latency bound from the plan Monitor could defer all stream output until done-sentinel without failing CI Record elapsed time from breadcrumb write to stdout emission; assert elapsed <= 2 when poll-interval=1
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: security: scripts/breadcrumb-monitor.sh:91-95,203-231
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Stream path is validated only at startup; the poll loop reads via dd without re-checking symlink or path containment. A local attacker racing to replace the stream file with a symlink after validation could cause the monitor to read arbitrary file bytes into chat (PEM redaction reduces but does not eliminate leakage of other sensitive content). Re-validate before each read using canonical path containment (pwd -P) matching lib-larch-log.sh, or reject -L on every poll iteration.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: code-quality: scripts/breadcrumb-monitor.sh:162-171
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] larch_bm_read_chunk slurps full delta into memory Large stream growth bursts can allocate multi-MiB strings in the monitor Use chunked reads or cap delta before command substitution
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: code-quality: scripts/larch-log.sh:127-143,scripts/refresh-run-logs.sh:5157-5162
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Implicit breadcrumb source derivation only Mis-set log-root yields no committed breadcrumbs without an explicit caller error Export LARCH_BREADCRUMB_SOURCE_DIR from refresh/finalize publish callers
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

