### FINDING_1: Restrict stalled detection to run-summary H2s
- **Reviewer(s)**: Codex-Arch, Cursor-Innovation, Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: blocking
- **Concern**: After the planned all-lines scan, the stalled-heading predicate is too loose: any line ending in `: stalled` or `— stalled` can satisfy it, so bullets like `- **Outcome**: stalled` may be treated as the summary heading and make recovered summaries look stalled, which can misdirect reconciliation and `_committed_summary_heading_is_stalled()`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: `Require an H2 anchor before matching, for example \`line.lstrip().startswith("## ")\` or an equivalent regex anchored to the heading prefix.`
  - From Cursor-Innovation: `Keep the all-lines scan, but tighten the predicate to run-summary H2 headings only (e.g. require \`stripped.startswith("## /")\` and a \` run \` token before the separator). Add a regression where a non-stalled H2 precedes \`- **Outcome**: stalled\` and helpers stay false / reconciliation stays off; keep the planned prelude-before-stalled-H2 positive case.`
  - From Cursor-Pragmatic: `When implementing the all-lines scan, require an H2 run-summary heading in \`_summary_heading_line_is_stalled()\` (for example \`stripped.startswith("## /")\` plus the existing stalled suffix test). Add a test where the H2 is non-stalled and a lower \`- **Outcome**: stalled\` line is present; both helpers must return false/None.`
  - From Codex-Pragmatic: `Require a heading prefix before accepting the stalled suffix, so only the \`## /<skill> run ...\` H2 lines are eligible for stalled detection.`


