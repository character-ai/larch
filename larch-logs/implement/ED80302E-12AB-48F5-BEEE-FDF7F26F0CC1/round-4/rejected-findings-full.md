### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: `larch_err` bypasses breadcrumb-monitor stream redaction
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Migrated callsites write dynamic progress directly to FD 4 via `larch_err`/`larch_errf`, bypassing the previous breadcrumb-monitor streaming redaction path. CI text, retry diagnostics, secrets, or temp paths may reach the operator transcript.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: Quiet-log-only publish may commit more material than old breadcrumbs
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Publishing full quiet logs rather than capped ndjson breadcrumb records may increase the amount of helper stderr captured under `larch-logs/breadcrumbs/`, raising exposure risk if redaction misses content.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: Family B monitor still watches an empty breadcrumb stream
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Family B flows still launch `breadcrumb-monitor` against `larch:bc` streams, but writers now use `larch_err` only. Background jobs may appear stuck in orchestrator chat until process exit because live monitor progress is empty.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: Legacy ndjson breadcrumbs are ignored during publish
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Breadcrumb publish is now quiet-log-only, so a mid-run Stage 1 to Stage 2 upgrade can commit successfully while dropping ndjson-only breadcrumb forensics without warning.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_16: run-logs docs still imply live stream files matter
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `docs/run-logs.md` still suggests live stream files under session `breadcrumbs/`, even though Stage 2 committed artifacts are quiet logs and stream files may be empty legacy allocations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: Inert `LARCH_QUIET_BREADCRUMBS` exports remain in runtime flow
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `skills/implement/SKILL.md` and related scripts still export `LARCH_QUIET_BREADCRUMBS=1`, but lib-quiet no longer consumes it. Operators may expect the variable to control live progress when behavior is unchanged.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

