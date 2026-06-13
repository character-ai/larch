### FINDING_1: Verbosity Control allow-list omits required non-Step-3 wait breadcrumbs
- **Reviewer(s)**: Codex-Arch, Codex-Requirements
- **Severity**: important
- **Concern**: The plan requires Step 5c and Final summary to print plain `⏳ ...` immediate-background wait breadcrumbs, but Verbosity Control still only permits start/skip breadcrumbs plus the Step 3 compact reviewer table. The prompt stays internally inconsistent, so agents may suppress the new required breadcrumb or treat it as disallowed output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: When updating the allowed-output bullet, explicitly permit plain immediate-background progress breadcrumbs such as `⏳ 5c...` and `⏳ final-summary...`, while keeping the `📊` reviewer table scoped only to Step 3 launch and Step 3 resume fences.
  - From Codex-Requirements: Update the planned Verbosity Control edit to allow plain immediate-background wait breadcrumbs required by specific non-Step-3 fences, while keeping the compact reviewer table Step-3-only.

