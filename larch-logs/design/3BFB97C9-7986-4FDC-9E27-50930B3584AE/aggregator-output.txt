### FINDING_1: New unclosed-fence test asserts against prior fixture
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Codex-Pragmatic, Codex-Requirements, Codex-dyn-test-edge-gap
- **Severity**: important
- **Concern**: The planned unclosed-fence regression creates a new fixture under `$TMP/unclosed-fence/plan.txt` but asserts against the existing `$DDED/plan.txt` section-aware fixture, so the test could fail for the wrong reason or fail to validate the new scenario.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Define a new fixture variable such as DUNCLOSED="$TMP/unclosed-fence", set DESIGN_TMPDIR to it, and assert grep -c for the actual duplicate bullet in "$DUNCLOSED/plan.txt"
  - From Codex-Edge: Assert against the new fixture variable or path, for example "$UNCL/plan.txt", and make the grep pattern match the duplicate line written into that fixture
  - From Codex-Pragmatic, Codex-Requirements: Use a new fixture variable such as DUNCLOSED="$TMP/unclosed-fence", set DESIGN_TMPDIR to it, and assert the duplicate count against "$DUNCLOSED/plan.txt"
  - From Codex-dyn-test-edge-gap: Use a fresh fixture variable for $TMP/unclosed-fence and assert against that variable's plan.txt

### FINDING_2: New unclosed-fence path does not assert stdout protocol
- **Reviewer(s)**: Cursor-dyn-stdout-protocol-drift, Codex-dyn-stdout-protocol-drift
- **Severity**: important
- **Concern**: The new unmatched-opener test only checks duplicate survival and explicitly skips the removed-count stdout assertion, so malformed stdout or debug output on that path could pass undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-stdout-protocol-drift, Codex-dyn-stdout-protocol-drift: Assert the exact `dedup-sweep: removed 0 duplicate line(s) from plan.txt` line in the new unclosed-fence case, using a fixture with no removable duplicates outside `## Constraints`.

### FINDING_3: Python failure mode does not match shell behavior
- **Reviewer(s)**: Cursor-dyn-stdout-protocol-drift, Codex-dyn-stdout-protocol-drift
- **Severity**: important
- **Concern**: The plan says a Python heredoc failure crashes Step 3, but the real `_run_post_apply_pipeline` call runs under `if !`, which can suppress `errexit` inside the function and allow an empty `dedup_removed` to fall through as `0`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-stdout-protocol-drift, Codex-dyn-stdout-protocol-drift: Add a minimum wrapper guard around the Python assignment: capture rc, require `dedup_removed` to match `^[0-9]+$`, and return failure before `mv -f` when it does not; update the failure-mode text to match that observed shell behavior.

### FINDING_4: Multiple-unbalanced-openers semantics conflict with single-slot stack rule
- **Reviewer(s)**: Cursor-dyn-test-edge-gap
- **Severity**: important
- **Concern**: The plan’s multiple-unbalanced-openers bullet implies a multi-entry stack dropped at EOF, while the nested-fence bullet requires only pushing when the stack is empty, risking a semantic change from the current toggle behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-test-edge-gap: Align bullet 44 with bullet 48: only the first unmatched opener occupies the stack; a later ```b with non-empty suffix is a failed closer attempt, not a second stack entry

### FINDING_5: Edge-case fence semantics are specified but not tested
- **Reviewer(s)**: Codex-dyn-test-edge-gap
- **Severity**: latent
- **Concern**: The plan specifies mismatched-tick and nested-looking fence semantics, but the planned tests cover only the basic unclosed-fence path and existing incidental balanced-fence cases, leaving room for behavior changes to pass unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-test-edge-gap: Keep the SIMPLE scope explicit: either add a brief coverage note that mismatched-tick and nested-looking cases are intentionally untested accepted risk, or fold one minimal assertion into the existing section-aware fixture to pin those two closer-rule cases
