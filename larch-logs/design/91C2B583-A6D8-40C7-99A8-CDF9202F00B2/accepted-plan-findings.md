### FINDING_1: Cursor argv profiles omit required subcommand and prompt flag
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: Cursor production launches require `cursor agent -p ...`, but the proposed profiles and tests omit both `agent` and `-p`, allowing incompatible argv to ship.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `agent` and `-p` immediately after `cursor` in all four Cursor profile specs, and extend the Cursor full-list argv tests to assert both on every profile.


### FINDING_2: Codex argv profiles omit `exec`
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Concern**: Production Codex launches require the `codex exec` command shape, but the proposed profiles and tests omit `exec`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: A builder or test written only from the plan can emit `codex --sandbox ...`, which is not the production command shape later pieces must match. Prefix both Codex profiles with `codex exec` in the Approach and add `exec` to the Codex full-list argv assertions.


### FINDING_3: Claude profiles lack the no-read-tools review shape
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Concern**: `launch_claude_review` may omit `--read-tools-add-dir`, but the proposed profiles provide no exact Claude argv profile for that base shape.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add a no-read-tools Claude review profile and test its exact argv and stdin behavior


### FINDING_6: Token-cap checks omit the timing step
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Concern**: Launchers pass `--step <timing_task_kind>` to `token check-budget`, but the proposed request and tests do not require this, risking incompatible cap-hit sidecars with `STEP=unknown`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add a `timing_task_kind` (or equivalent) field on the frozen launch request, pass it as `--step` in the cap-check argv, and extend the cap-command tests to pin the full argv including `--step`.


### FINDING_7: Retry exhaustion may suppress completion promotion
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Concern**: The proposed lifecycle may fail to promote the terminal `.inner.done` marker after retries end with a nonzero result, even when postprocessing and accounting succeed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Promote completion after a terminal nonzero result when all hooks succeed. Suppress promotion only when timing, postprocessing, or usage raises. Test promotion and hook-failure suppression for both zero and nonzero results.


