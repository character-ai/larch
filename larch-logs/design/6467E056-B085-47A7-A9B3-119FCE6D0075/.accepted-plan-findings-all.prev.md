### FINDING_1: Publish-tail abort paths still mandate file Read, not marker extraction
- **Reviewer(s)**: Cursor-Arch, Codex-Innovation, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: The plan adds `LARCH_FINAL_SUMMARY_BEGIN`/`END` emission from `design-step5c.sh` on publish-tail abort (`_publish_rc`=2 and unexpected non-zero outside `{0,1,3,4}`), but `skills/design/SKILL.md` **Driver exit-code contract** (~859–863) still tells the orchestrator to stop before Step 5c items 5–7 and to Read/`cat` `final-summary.md` for abort-path summary emission. On those paths the marked body in captured stdout would not be re-emitted, violating the acceptance goal of no separate Read on failure paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add an explicit `### UPDATED: skills/design/SKILL.md` bullet for the **Driver exit-code contract** paragraph: parse markers from `design-step5c.sh` stdout on abort paths with the same fallback gate as item 5
  - From Codex-Innovation: Update the driver exit-code contract to extract and verbatim emit `LARCH_FINAL_SUMMARY_BEGIN/END` output before aborting, with the same non-empty file fallback and sidecar handoff rules
  - From Codex-Pragmatic: Update the driver exit-code contract to extract the marked body from completed `design-step5c.sh` output before sidecars and before stopping, or define marker extraction as a shared handoff that runs for rc 0/1/3 plus abort rc 2/unexpected
  - From Cursor-Requirements: Extend the `SKILL.md` update list to rewrite the failed-publish-tail abort emission prose (~line 859) to extract `LARCH_FINAL_SUMMARY_BEGIN/END` from `design-step5c.sh` captured stdout first, with the same non-empty-file Read fallback used elsewhere
  - From Codex-Requirements: Update the Step 5c driver exit-code contract to extract and re-emit `LARCH_FINAL_SUMMARY_BEGIN/END` output before sidecar emission and abort, with the same non-empty file fallback when markers are absent or invalid


### FINDING_3: Step 0 early cancel routes still require separate file Read
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: Acceptance requires no Read call for cancellation summary emission, but `cancel-title-filter` and `cancel-reentry-guard` still render via `design-route.sh` with stdout redirected to `/dev/null`, `design-step0-route.sh` captures and deletes route stdout, and `SKILL.md` line 286 still instructs the orchestrator to read `final-summary.md`. Those cancellation paths would retain the separate Read this PR is meant to remove.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Extend the marker contract to these early cancel routes. Have the route wrapper emit or forward `LARCH_FINAL_SUMMARY_BEGIN/END` around `final-summary.md` before deleting captured output, and update `SKILL.md` line 286 to parse markers with the same non-empty-file Read fallback




### FINDING_1: Compatibility stub may exec prepare with empty argv
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: If `design-step5.sh` is kept as a backward-compat pass-through stub, the planned pattern of `exec design-step5b-prepare.sh "$@"` after the wrapper argparse loop leaves `"$@"` empty because the launcher already consumed `--session-env-path` and `--claude-pid`. Paused or legacy callers that still invoke `design-step5.sh` could reach prepare without those flags and skip `design_source_env_optional` when exports are missing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Exec prepare with explicit `--session-env-path "$SESSION_ENV_PATH" --claude-pid "$CLAUDE_PID"` (or re-source source-env.sh immediately before exec); do not rely on empty `"$@"`


### FINDING_3:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:65-76
- **Concern**: [SCOPE-REDUCTION] Step 0 route marker work expands the change beyond the Step 5 and Final summary fence scope. Scenario: The issue names design-step5c.sh and design-step-final-summary.sh as the marker emitters; adding design-step0-route.sh and design-route.md changes the Step 0 router/cancel contract and KV handoff without being required for the Step 5 minimum-change feature
- **Proposed resolution**: Drop the planned design-step0-route.sh, design-step0-route.md, design-route.md, SKILL Step 0 cancellation, and structure-test changes; keep marker extraction to Step 5c and the existing Final summary block



