# Review Round 2

- Mode: `diff`
- 2 accepted, 3 rejected (0 neutral)

## Accepted Findings

### FINDING_3: Step 8 probe still accepts a bare tmpdir expansion
- **Reviewer(s)**: cursor-specialist-edge-cases, codex-specialist-edge-cases
- **Severity**: important
- **Concern**: `skills/shared/orchestrator-never.md` still documents a bare `test -f "$IMPLEMENT_TMPDIR/.step-8-ship-handoff.rc"` probe, so a fresh shell can test the root-relative path instead of the resolved ship-handoff file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: `Replace section text with pointer-resolved probe; add harness pin`
  - From codex-specialist-edge-cases: `Remove the trailing compatibility section, or update it to the same pointer-resolved \`IMPLEMENT_TMPDIR=$(awk ... current-implement-env-$PPID.sh); test -f "$IMPLEMENT_TMPDIR/.step-8-ship-handoff.rc"\` form used by the main contract and hook tests.`


### FINDING_7: Architectural-guideline assessment file still trusts caller expansion
- **Reviewer(s)**: codex-specialist-edge-cases, dyn-dyn-launcher
- **Severity**: important
- **Concern**: `skills/implement/references/architectural-guidelines-present.md` still passes a shell-expanded assessment-file argv value, so fresh-shell calls can lose the tmpdir prefix before the wrapper reads the file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: `Rebase/default the assessment-file path inside `step-architectural-guidelines-write-staged.sh`, or change the wrapper to derive the assessment path from exported IMPLEMENT_TMPDIR instead of trusting a caller-expanded argv path.`
  - From dyn-dyn-launcher: `Either pass a tmpdir-relative leaf (and resolve under exported `IMPLEMENT_TMPDIR` in the wrapper), or add the same root-relative rebase helper to `write-staged-assessment` before reading `--assessment-file`.`


