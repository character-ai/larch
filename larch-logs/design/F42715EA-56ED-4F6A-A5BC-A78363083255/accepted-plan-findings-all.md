### FINDING_1: Honor `force_conditional` when classifying background references
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: `force_conditional` is introduced on `DirectiveMatch`, but `_paths_for_directive_match` still decides conditional status only from `conditional_section` and `_line_is_conditional(...)`. That leaves background-only `see ... only for background` table rows classified as eager and can push `flags.md` out of `conditional_files`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In _paths_for_directive_match set is_conditional = context.conditional_section or context.match.force_conditional or _line_is_conditional(...). Set force_conditional=True on background-regex DirectiveMatch objects. Add a unit test using a when-free table-row-style line (per-round-approval wording) so the bug is not masked by rows that happen to contain when 1.
  - From Cursor-Innovation: In _paths_for_directive_match, treat context.match.force_conditional as forcing is_conditional=True before _extract_repo_paths, so every only-for-background hit goes to conditional_files.
  - From Cursor-Pragmatic: In lint_skill_closure_growth.py, set is_conditional from match.force_conditional before conditional_section and _line_is_conditional; document that hook in the plan UPDATED section


