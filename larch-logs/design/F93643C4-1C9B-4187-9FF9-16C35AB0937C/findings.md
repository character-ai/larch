### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/scripts/step-16-17.sh:1-40
- **Concern**: [SCOPE-REDUCTION] New `---LARCH-SUMMARY-FINAL-BEGIN/END---` markers duplicate an existing cross-skill handoff pattern. Scenario: `/design` already standardizes on whole-line `LARCH_FINAL_SUMMARY_BEGIN` / `LARCH_FINAL_SUMMARY_END` in `skills/design/scripts/design-step-final-summary.sh` and marker-extraction prose in `skills/design/SKILL.md`; a second marker grammar adds parser/orchestrator divergence and extra harness pins without changing behavior
- **Proposed resolution**: Reuse the design marker literals in `step-16-17.sh` and `skills/implement/SKILL.md`; keep implement SKILL bash fences marker-free per `scripts/test-implement-structure.sh:215-229`

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/step-16-17.sh:35-39
- **Concern**: Marker gate prose conflates Python rc with step-17.sh shell exit. Scenario: The plan gates markers on STEP17_RC=0, but also describes the gate as Step 17 render success. step-17.sh --no-print-stdout is specified to exit 0 after a post-persist upsert/stamp failure when summary-final.md bytes changed (python/pr_body.py:988-1026). An implementer could gate on Python rc=0 inside the wrapper and suppress markers on the valid handoff path, or emit markers on stale files if they gate only on file presence.
- **Proposed resolution**: Define the gate once as captured step-17.sh --no-print-stdout shell exit plus non-empty summary-final.md, and state explicitly that shell exit 0 may occur when Python returned non-zero but snapshot handoff approved.

### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: scripts/test-implement-structure.sh:140
- **Concern**: Planned harness pin says marker emission is gated on "Step 17 render success". Scenario: That wording matches Python rc=0, not the planned shell handoff where step-17.sh --no-print-stdout exits 0 after a refreshed summary-final.md even when final-report write returns non-zero for stamp/upsert failure (python/pr_body.py:988-1026). Implementers can suppress markers on the required upsert-failure handoff path.
- **Proposed resolution**: Reword the pin to gate on captured step-17 exit code 0 (handoff contract), explicitly including the post-persist non-zero Python path; add a negative pin that markers must still emit when only stamp/upsert failed after a byte change.
