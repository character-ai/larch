### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: risk-integration: repo-wide
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No static enforcement that emit_breadcrumb includes --category= in stream-relevant scripts Future edit without --category= passes CI until runtime stream is set and breadcrumbs silently drop Add lint target grepping production scripts for uncategorized emit_breadcrumb
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: risk-integration: scripts/test-lib-quiet.sh:141-155
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] No emit_breadcrumb_stderr no-newline larch_errf fallback test Dot-progress stderr byte contract relies on indirect ci-wait coverage Add stream-unset/stream-set test for emit_breadcrumb_stderr --category=wait-ci "."
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: risk-integration: scripts/test-breadcrumb-monitor.sh:265-290
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Test 7 does not bound stream growth latency to poll-interval plus 1s Slow monitor poll would not be detected by current end-state grep only Record time before append; assert output within 2s with poll-interval=1
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: code-quality: scripts/lib-quiet.sh:210-297
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicate --category= parsing in emit_breadcrumb and emit_breadcrumb_stderr Future category-option changes must be edited twice increasing drift risk Extract a shared larch_quiet_shift_bc_category helper used by both emitters
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: security: scripts/lib-larch-log.sh:391-425
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Symlink check before read is subject to TOCTOU A race can turn a validated breadcrumb path into a symlink to host files before redact-tmpdir-paths/redact-secrets reads it Open via no-follow or copy-through staging after verifying a stable regular file identity
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_27

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_27: risk-integration: scripts/larch-log.sh:127-142
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Missing/empty breadcrumb source skips publish and preserves prior committed breadcrumbs Tmpdir breadcrumbs cleared before final commit leaves stale larch-logs/.../breadcrumbs/ while other run artifacts update Document behavior or warn/replace when committed breadcrumbs exist but source is empty
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_3: code-quality: scripts/test-breadcrumb-monitor.sh:44-51
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] make_monitor_fixture copies unused larch-log-batches.sh Fixture trees carry a misleading dependency and extra file I/O per test Remove the larch-log-batches.sh copy from make_monitor_fixture
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_30

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_30: architecture: scripts/breadcrumb-monitor.sh:103-115
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Rate cap permanently drops breadcrumb lines Burst progress during ship-pr/Step 5 can lose stall or escalate messages Defer capped lines or exempt high-severity categories from cap
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: code-quality: scripts/ci-wait.sh:282
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] suspend message uses warn instead of plan network-flake category Structured consumers cannot distinguish suspend/network-flake from generic warnings Use --category=network-flake or document warn as intentional in ci-wait.md
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

