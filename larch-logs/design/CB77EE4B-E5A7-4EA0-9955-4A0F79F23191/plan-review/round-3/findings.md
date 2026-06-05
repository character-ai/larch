### FINDING_1:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:10-23
- **Concern**: Helper/test plan does not require tab-delimited parsing for @tsv output. Scenario: An awk implementation using default whitespace FS will miscount files with spaces in their names, e.g. docs/user guide.md shifts additions/deletions fields and silently corrupts the line totals
- **Proposed resolution**: Require awk -F '\t' or an equivalent IFS-tab reader, and add a fixture with a filename containing a space

### FINDING_2:
- **Reviewer(s)**: Cursor-dyn-harness-gap
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-render-run-summary.sh:27-62
- **Concern**: Plan adds grep for `Lines (PR diff): code +` but not the argv setup that produces it. Scenario: The primary implement fixture never passes `--code-added`/`--code-deleted`/`--logs-added`/`--logs-deleted`, so the new assertion cannot pass as written
- **Proposed resolution**: In the same plan section, require extending the full-input implement invocation (and any other positive case) with the four line-count flags before adding the `code +` grep

### FINDING_3:
- **Reviewer(s)**: Codex-dyn-harness-gap
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:22-23
- **Concern**: Finding 1: The empty-repo endpoint assertion is specified, but the planned gh shim only says it prints a fixed TSV fixture and does not say it records or echoes the requested endpoint.. Scenario: The harness cannot mechanically prove the helper called repos/{owner}/{repo}/pulls/<N>/files instead of a bare pulls/<N>/files path while staying offline.
- **Proposed resolution**: Keep the harness simple: make the gh PATH shim append its argv or endpoint argument to a temp log, then grep that log for repos/{owner}/{repo}/pulls/<N>/files in the empty --repo case.

### FINDING_4:
- **Reviewer(s)**: Codex-dyn-harness-gap
- **Severity**: latent
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:28-33; skills/implement/scripts/test-write-final-report.sh:439-465
- **Concern**: Finding 2: The plan adds a Lines bullet to compose_self_fallback, but the write-final-report harness plan only asserts normal end-to-end Lines output and N/A paths; the existing stage2 self-fallback schema check is not updated to assert the new fallback Lines bullet.. Scenario: A regression could omit Lines (PR diff) only in the degraded self fallback while all planned harness assertions still pass.
- **Proposed resolution**: Add one minimal assertion to the existing stage2 fallback block for - **Lines (PR diff)**: N/A, or include that bullet in the ordered schema list after Code review.
