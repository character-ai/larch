### FINDING_1: Require tab-delimited parsing for TSV diff stats
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Concern**: Helper/test plan does not require tab-delimited parsing for @tsv output. Scenario: An awk implementation using default whitespace FS will miscount files with spaces in their names, e.g. docs/user guide.md shifts additions/deletions fields and silently corrupts the line totals
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Require awk -F '\t' or an equivalent IFS-tab reader, and add a fixture with a filename containing a space


### FINDING_2: Extend render summary test argv before asserting line-count output
- **Reviewer(s)**: Cursor-dyn-harness-gap
- **Severity**: important
- **Concern**: Plan adds grep for `Lines (PR diff): code +` but not the argv setup that produces it. Scenario: The primary implement fixture never passes `--code-added`/`--code-deleted`/`--logs-added`/`--logs-deleted`, so the new assertion cannot pass as written
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-harness-gap: In the same plan section, require extending the full-input implement invocation (and any other positive case) with the four line-count flags before adding the `code +` grep


### FINDING_3: Log gh shim endpoint so empty-repo path can be asserted offline
- **Reviewer(s)**: Codex-dyn-harness-gap
- **Severity**: important
- **Concern**: The empty-repo endpoint assertion is specified, but the planned gh shim only says it prints a fixed TSV fixture and does not say it records or echoes the requested endpoint. Scenario: The harness cannot mechanically prove the helper called repos/{owner}/{repo}/pulls/<N>/files instead of a bare pulls/<N>/files path while staying offline.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-harness-gap: Keep the harness simple: make the gh PATH shim append its argv or endpoint argument to a temp log, then grep that log for repos/{owner}/{repo}/pulls/<N>/files in the empty --repo case.


### FINDING_4: Assert Lines bullet in degraded self-fallback schema
- **Reviewer(s)**: Codex-dyn-harness-gap
- **Severity**: latent
- **Concern**: The plan adds a Lines bullet to compose_self_fallback, but the write-final-report harness plan only asserts normal end-to-end Lines output and N/A paths; the existing stage2 self-fallback schema check is not updated to assert the new fallback Lines bullet. Scenario: A regression could omit Lines (PR diff) only in the degraded self fallback while all planned harness assertions still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-harness-gap: Add one minimal assertion to the existing stage2 fallback block for - **Lines (PR diff)**: N/A, or include that bullet in the ordered schema list after Code review.

