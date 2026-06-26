## Decision 1: Which fix option (Option 1 vs Option 2)
- **Question**: Should the fix move the marker in `compose-report` output (Option 1), or preserve leading comments in `issue parse-input` (Option 2)?
- **Resolution**: Option 1 (move marker to immediately after `### title` in `_compose_tier_a_issue`). This aligns with the documented contract in `stall-recovery-report.md` ("Tier A places the marker immediately after the `###` title line") and mirrors how Tier B (`chat-print`) already places the marker (`f"### {title}\n\n{_report_marker(report_sig)}\n"`). Option 2 would require changes to `parse_issue_input`, which affects a shared path used by OOS filers and review pipelines.
- **Source**: codebase
