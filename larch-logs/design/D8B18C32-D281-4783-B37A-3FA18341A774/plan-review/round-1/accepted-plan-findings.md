### FINDING_1: Step-4 test may not verify the actual issue input file
- **Reviewer(s)**: Cursor-Edge, Cursor-Pragmatic
- **Severity**: latent
- **Concern**: The Step-4 wiring test only checks for the `issue-input-file` token and could pass even if `/larch:issue --input-file` is wired to the wrong file, allowing a silent no-file or zero-item filing path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge, Cursor-Pragmatic: Require step 4 to reference stall-recovery-issue-input.md on the /larch:issue --input-file line, or assert stall-recovery-bug-body.md is not that target (e.g. grep -Fq stall-recovery-issue-input.md on the --input-file path)


### FINDING_2: Batch issue output keys need normalization
- **Reviewer(s)**: Codex-Edge, Codex-Pragmatic
- **Severity**: important
- **Concern**: Step 4 still describes persisting top-level `ISSUE_NUMBER` / `ISSUE_URL` after switching to `/larch:issue --input-file`, but batch mode emits indexed keys such as `ISSUE_1_NUMBER` and `ISSUE_1_URL`; without normalization, later terminal-failure comments may not target the recovery-created issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: In the Step 4 rewrite, state that stdout from /issue batch mode must be normalized: persist ISSUE_1_NUMBER/ISSUE_1_URL as ISSUE_NUMBER/ISSUE_URL, and use ISSUE_1_DUPLICATE_OF_NUMBER/URL when the item deduplicates.
  - From Codex-Pragmatic: Make Step 4 explicitly normalize ISSUE_1_NUMBER and ISSUE_1_URL from /larch:issue stdout into ISSUE_NUMBER and ISSUE_URL in stall-recovery-issue.env when the single-item batch create succeeds.


### FINDING_3: Step token sanitizer permits unsafe trailing text
- **Reviewer(s)**: Codex-dyn-script-inventory
- **Severity**: important
- **Concern**: `safe_step_value` is not fully parser-safe for step-family values because the glob permits arbitrary trailing bytes after an initial safe character, and the result can be copied into a public issue title.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-script-inventory: Tighten safe_step_value with a full-string regex or closed enum for the intended step tokens before composing the title, and add one regression fixture for an 8a-prefixed unsafe value


