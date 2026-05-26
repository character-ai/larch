### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: security: scripts/lib-larch-log.sh:246-277
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Publish checks symlinks on the breadcrumbs dir and each .ndjson file but not on session *_TMPDIR ancestors. If IMPLEMENT_TMPDIR is a symlink to a wider tree, prefix checks pass and publish reads outside the intended isolated tmpdir. Resolve non-symlink canonical session roots at publish time and require the breadcrumb source to stay under that root.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: security: SECURITY.md:128-141
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Documented residual risk: operational wait-ci/warn breadcrumb text may be committed after secrets redaction. A failed CI wait can write check names, URLs, or failure snippets into committed larch-logs breadcrumbs visible in the public repo. Keep as documented accepted risk; cross-link from docs/run-logs.md for operator awareness.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: correctness: scripts/larch-log.sh:127-142
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Empty breadcrumbs_source when log-root is not */larch-logs silently skips publish Caller passes non-standard --log-root without LARCH_BREADCRUMB_SOURCE_DIR; commit succeeds without breadcrumbs/ while tmpdir still has live streams Fail closed or warn when tmpdir breadcrumbs exist but source resolution fails
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_19: correctness: scripts/lib-larch-log.sh:293
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Commit reads session ndjson without synchronizing with active writers refresh-run-logs commit overlaps ship-pr/ci-wait appends; committed file can contain torn lines or partial secrets Follow done-sentinel gating snapshot copy or document commit-only-after-monitor-complete
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: code-quality: scripts/breadcrumb-monitor.sh:28-43;scripts/lib-larch-log.sh:217-231
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Session tmpdir allowlist implemented twice for monitor vs larch-log publish Future session root (or path check fix) updated in only one copy breaks either monitor validation or commit-time publish Extract one shared under-session-tmp helper used by both call sites
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_20: risk-integration: scripts/breadcrumb-monitor.sh:117-128
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Rate cap silently drops breadcrumb lines Burst CI dot progress during wait-ci exceeds RATE_CAP; chat loses progress with only WARN rate-capped Coalesce capped output or raise wait-ci cap
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: code-quality: scripts/test-breadcrumb-monitor-bash32.sh:22
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Bash32 harness only re-execs main test without explicit parity assertion Plan wording implied stronger parity check than implemented Document intent or add minimal golden/exit parity assertion
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: code-quality: scripts/ship-pr.sh:2160-2161
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Dual stall+escalate breadcrumbs for one waterfall exhaustion Monitor/chat may show duplicate warnings for one event Collapse to one categorized breadcrumb if redundant
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

