### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: risk-integration: scripts/test-ci-wait.sh:245-261
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] no stream-set test for ci-wait bail/warn emit_breadcrumb_stderr paths Bail under background ci-wait could leak progress to stderr or omit c=warn from stream without failing CI Add STUB_STATUSES=fail or timeout case with stream set asserting c=warn and quiet stderr
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: risk-integration: scripts/test-ci-wait.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] no golden stderr byte comparison for stream-unset emit_breadcrumb_stderr fallback Regression could change dot-progress stderr formatting without failing functional grep checks Capture and assert stderr baseline on stream-unset runs
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: risk-integration: scripts/test-lib-quiet.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] missing producer test for uncategorized emit_breadcrumb when stream is set lib-quiet could stop warning on missing category while monitor tests still pass Add stream-set helper asserting WARN and no stream record
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: risk-integration: scripts/test-breadcrumb-monitor.sh:261-287
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] test 7 lacks poll-interval+1s latency assertion Slow or broken polling could still pass while violating streaming SLO Record time-to-first-line and assert <= poll-interval + 1
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: risk-integration: scripts/test-design-log-publish.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] no design publish breadcrumb redaction integration test design_publish_breadcrumbs wiring could regress independently of implement commit tests Add minimal DESIGN_TMPDIR/breadcrumbs PEM fixture and assert redacted design run log output
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_19: security: scripts/lib-quiet.sh:149-150
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Structured breadcrumb text= field is unescaped space-delimited text Forged or crafted stream line can deliver misleading progress text to orchestrator after redaction of PEM/token families only Encode text field structurally (JSON/length-prefix) and parse without awk token heuristics
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_24

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_24: correctness: scripts/lib-larch-log.sh:293
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Committed breadcrumb redaction can read concurrently growing ndjson files. Refresh commit overlaps a still-running Family B writer; committed file may contain torn lines. Copy source to staging before redact or require done-sentinel before publish; document caller invariant.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_25

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_25: architecture: scripts/lib-larch-log.sh:254-256
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Path-scope relies on exported session tmp env vars in the publishing process. Caller passes valid absolute breadcrumbs path but omits export IMPLEMENT_TMPDIR; publish fails closed. Derive allowed root from LARCH_LOG_ROOT parent when log-root matches */larch-logs.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_26

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_26: risk-integration: scripts/refresh-run-logs.sh:137-138
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Commit stderr suppressed on refresh path. Breadcrumb redaction fail-closed message never reaches operator; only REFRESH_COMMITTED=false. Propagate larch-log.sh stderr into refresh KEY=value output or larch_err.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: code-quality: scripts/breadcrumb-monitor.sh:27-44
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicated session-tmp path allowlist vs lib-larch-log.sh RESEARCH_TMPDIR or future tmpdir support may be added to only one copy Extract shared larch_session_tmp_allows_path helper used by monitor and log publish
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_30

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_30: correctness: scripts/ship-pr.sh:2160
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] ⚠-prefixed recovery message uses --category=stall contrary to plan emoji routing (⚠ → warn). Consumers filtering c=stall mis-label waterfall exhaustion handoff. Change to --category=warn or align message prefix with stall semantics.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: code-quality: scripts/breadcrumb-monitor.sh:209-222
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Dead no-op buf blocks after flush removal Reader cannot tell whether intentional partial-line suppression or incomplete refactor Remove blocks or restore flush logic
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: code-quality: skills/cleanup/scripts/cleanup.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] --category= added outside plan stream-relevant scope Extra diff noise without stream-set behavior change Revert or document global category requirement in lib-quiet.md
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

