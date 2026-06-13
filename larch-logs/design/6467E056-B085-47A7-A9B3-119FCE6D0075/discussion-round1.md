## Decision 1: OOS stdout bridge approach
- **Question**: Write-tool directive (SKILL.md prose change) vs `--issue-stdout-file` on annotate wrapper?
- **Resolution**: Write-tool directive — change SKILL.md prose from shell `printf` to direct Write tool instruction. No script changes needed for this piece.
- **Source**: codebase (design-step5b-annotate.sh already uses `--issue-stdout-file "$DESIGN_TMPDIR/oos-issue.stdout.txt"`; the bridge problem is purely in SKILL.md prose)

## Decision 2: Marker placement for final-summary.md emission
- **Question**: Add markers in render-final-summary.sh (shared) vs in the two caller wrappers?
- **Resolution**: Add markers in `design-step5c.sh` and `design-step-final-summary.sh`. render-final-summary.sh runs inside design-publish.sh with stdout captured to a temp file; markers there would not reach the task output. Wrappers emit markers directly after the render helper finishes.
- **Source**: codebase (design-step5c.sh pipes design-publish.sh stdout to a temp file)

## Decision 3: Marker format
- **Question**: What token names?
- **Resolution**: `LARCH_FINAL_SUMMARY_BEGIN` / `LARCH_FINAL_SUMMARY_END` on dedicated lines in stdout. Present also in abort_failed_publish_tail path in design-step5c.sh.
- **Source**: codebase conventions + acceptance criteria ("stable")

## Decision 4: Backward compatibility fallback
- **Question**: Hard-require markers or fall back to Read for resumed/older sessions?
- **Resolution**: Keep file-based emission as fallback in SKILL.md ("when markers absent, fall back to Read if file is non-empty"). Scripts still write final-summary.md to disk.
- **Source**: acceptance criteria ("all existing emission gates preserved")

## Decision 5: REPORT_GATE_SIDECARS_FILE path
- **Question**: Also convert sidecars to markers?
- **Resolution**: Keep as file-path reference (issue mentions only final-summary.md; sidecars are a separate concern).
- **Source**: issue body scope ("Step 5c and the cancellation Final summary fence both require a separate Read of final-summary.md")

3 decisions resolved; 2 design-decision confirmations from codebase.
