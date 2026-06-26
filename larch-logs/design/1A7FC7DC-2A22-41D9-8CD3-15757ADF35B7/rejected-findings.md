### [Plan Review] FINDING_3

### FINDING_3: orchestrator-never.md top-contract rewrite lacks /research carve-out
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The plan rewrites the `orchestrator-never.md` header to say skills read the file only when explicitly referenced, but `skills/research/SKILL.md` (~110–114) still mandates a session-start full read via `MANDATORY at session start`. Post-change shared authority would contradict an existing lint-pinned consumer; implementers may delete eager-load wording that `/research` still depends on.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add an explicit carve-out: `/research` retains session-start full read; conditional-read wording applies to `/design` and `/implement` only.


### [Plan Review] FINDING_5

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:210-232
- **Concern**: [SCOPE-REDUCTION] Firm test-design-structure.sh recovery mirror duplicates test-implement-anti-polling-rule.sh while the mirror spec is incomplete. Scenario: Anti-polling already owns full negative pins (179-206) and positive split-branch pins (188-193); promoting test-design-structure.sh adds parallel maintenance without new coverage, and the truncated mirror block (224-225) is error-prone
- **Proposed resolution**: Drop the firm test-design-structure.sh anti-polling mirror (keep existing design-structure concerns only) or, if retained, paste lines 183-193 verbatim into that subsection and drop duplicate assertions from the anti-polling harness only after parity is explicit


