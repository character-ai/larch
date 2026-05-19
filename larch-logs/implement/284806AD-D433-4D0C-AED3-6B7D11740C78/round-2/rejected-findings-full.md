### [rejected] FINDING_13

### FINDING_13: correctness: scripts/scout-dynamic-archetypes.sh; scripts/scout-dynamic-archetypes.md
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Plan Part C enumerated three scout-local SCOUT_FAIL_REASON tokens; implementation adds invalid_archetypes_shape and fence_strip_io plus tests/docs. Readers comparing only the plan bullets might think telemetry is incomplete when it is not. Amend planning docs to list the full token enum or treat as acceptable plan underspecification.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=1 NEUTRAL=0

### [rejected] FINDING_20

### FINDING_20: security: skills/review/scripts/dispatch-panel.sh:272-289
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Unescaped SCOUT_FAIL_REASON and SCOUT_MANIFEST are interpolated into a double-quoted --entry argument when calling append-execution-issue.sh. Bash expands command substitutions inside the expanded string, so a crafted scout status sidecar (or other source) setting SCOUT_FAIL_REASON to e.g. $(malicious) can execute arbitrary commands during parse-failed handling. Pass the message via --entry-file from a tempfile, or sanitize/allowlist reason tokens, or build argv without double-quote expansion of untrusted substrings.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 NEUTRAL=0

### [rejected] FINDING_7

### FINDING_7: architecture: skills/review/SKILL.md; skills/review/references/heavy-worker.md
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Plan file list omitted these updates but branch changes them for SCOUT_FAIL_REASON KV handling. Orchestration docs drift from the written seven-file plan checklist only; behavior is aligned with the feature. Update the implementation plan template or accept as intentional ancillary doc sync.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 NEUTRAL=0

### [rejected] FINDING_8

### FINDING_8: code-quality: scripts/scout-dynamic-archetypes.sh:263-265
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] SCOUT_FAIL_REASON=fence_strip_io is emitted on mktemp failure, which is not fence-specific. Operators mis-attribute temp-file failures as fence-strip I/O in SCOUT_FAIL_REASON aggregates. Rename token or emit a distinct reason for mktemp failures.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=1 NEUTRAL=0

### [rejected] FINDING_9

### FINDING_9: code-quality: scripts/test-scout-dynamic-archetypes.sh:30-38
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] jq test stub keys only argv positions -c and --argjson Reordering scout's jq invocation can silently stop covering validation_jq_error Stub on full argv/env sentinel instead of fixed positional args
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=1 NEUTRAL=0

