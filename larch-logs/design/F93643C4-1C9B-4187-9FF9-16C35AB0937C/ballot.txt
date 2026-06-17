### FINDING_1: Marker gate must follow step-17.sh shell handoff, not Python rc alone
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: blocking
- **Concern**: Plan prose and harness pins conflate Python `final-report write` return code with Step 17 render/handoff success. The plan gates summary markers on `STEP17_RC=0` while also describing the gate as "Step 17 render success," which implementers may read as Python `rc=0`. `step-17.sh --no-print-stdout` is specified to exit `0` after a post-persist upsert/stamp failure when `summary-final.md` bytes changed (`python/pr_body.py:988-1026` writes the file, then may return non-zero after stamp/upsert failure while still printing the body on `--print-stdout`). An implementer could suppress markers on the required upsert-failure handoff path by gating on Python `rc=0` inside the wrapper, or emit markers from stale files by gating only on file presence without the shell handoff contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Define the gate once as captured step-17.sh --no-print-stdout shell exit plus non-empty summary-final.md, and state explicitly that shell exit 0 may occur when Python returned non-zero but snapshot handoff approved.
  - From Cursor-Pragmatic: Reword the pin to gate on captured step-17 exit code 0 (handoff contract), explicitly including the post-persist non-zero Python path; add a negative pin that markers must still emit when only stamp/upsert failed after a byte change.

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/scripts/step-16-17.sh:1-40
- **Concern**: [SCOPE-REDUCTION] New `---LARCH-SUMMARY-FINAL-BEGIN/END---` markers duplicate an existing cross-skill handoff pattern. Scenario: `/design` already standardizes on whole-line `LARCH_FINAL_SUMMARY_BEGIN` / `LARCH_FINAL_SUMMARY_END` in `skills/design/scripts/design-step-final-summary.sh` and marker-extraction prose in `skills/design/SKILL.md`; a second marker grammar adds parser/orchestrator divergence and extra harness pins without changing behavior
- **Proposed resolution**: Reuse the design marker literals in `step-16-17.sh` and `skills/implement/SKILL.md`; keep implement SKILL bash fences marker-free per `scripts/test-implement-structure.sh:215-229`
