### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: correctness: scripts/ship-pr.sh:2160
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] warn-prefixed message uses --category=stall Consumers surfacing only c=warn omit recovery-waterfall-exhausted stall-tagged line Use --category=warn per emoji-prefix routing or reword with stall emoji
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: code-quality: scripts/larch-log.sh:562-578
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Mis-shaped --log-root skips breadcrumbs silently via larch_log_breadcrumb_source_dir || true Non-standard log roots with live session breadcrumbs/ never commit streams without warning Warn or fail when breadcrumbs exist under session tmpdir but source resolution fails
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: code-quality: scripts/lib-quiet.md:20-30
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Docs omit LARCH_BREADCRUMB_STREAM and mandatory --category= vocabulary Authors may migrate callsites without categories and get dropped stream records Document stream contract and valid categories alongside emit_breadcrumb_stderr
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: code-quality: scripts/test-breadcrumb-monitor-bash32.sh:22
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Bash32 harness re-execs tests without byte-for-byte parity assertion Plan wording implies diff vs default bash run; only skip-or-run is implemented Document parity as re-exec only or capture and diff outputs from both shells
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: code-quality: scripts/ship-pr.sh:2160-2161
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Double emit_breadcrumb for one Phase 1-4 handoff (stall then escalate) Monitor shows duplicate warnings for one event; category filters see two records Use single category per handoff unless downstream requires both
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

