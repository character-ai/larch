### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:25-30
- **Concern**: New unclosed-fence test asserts against the prior section-aware fixture variable instead of the new fixture directory. Scenario: If implemented literally, the test either fails by grepping the old $DDED/plan.txt or fails to prove the new $TMP/unclosed-fence/plan.txt fixture preserved duplicate Constraints bullets
- **Proposed resolution**: Define a new fixture variable such as DUNCLOSED="$TMP/unclosed-fence", set DESIGN_TMPDIR to it, and assert grep -c for the actual duplicate bullet in "$DUNCLOSED/plan.txt"

### FINDING_2:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-plan-review-loop.sh:1664,1746 planned assertion
- **Concern**: New unclosed-fence test asserts against the previous DDED fixture instead of the new fixture. Scenario: The plan creates $TMP/unclosed-fence/plan.txt, then says to grep "$DDED/plan.txt"; that reads the section-aware test fixture from lines 1664-1702, so the regression either fails for the wrong reason or does not validate the proposed unclosed-fence output
- **Proposed resolution**: Assert against the new fixture variable or path, for example "$UNCL/plan.txt", and make the grep pattern match the duplicate line written into that fixture

### FINDING_3:
- **Reviewer(s)**: Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/test-plan-review-loop.sh:1663-1747
- **Concern**: New regression test asserts against the prior fixture path. Scenario: The plan says to build the unclosed-fence fixture under $TMP/unclosed-fence/plan.txt but then asserts grep against $DDED/plan.txt from the existing section-aware case, so following the plan would either fail for the wrong reason or not validate the new fixture
- **Proposed resolution**: Use a new fixture variable such as DUNCLOSED="$TMP/unclosed-fence", set DESIGN_TMPDIR to it, and assert the duplicate count against "$DUNCLOSED/plan.txt"

### FINDING_4:
- **Reviewer(s)**: Cursor-dyn-stdout-protocol-drift, Codex-dyn-stdout-protocol-drift
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:30; skills/design/scripts/test-plan-review-loop.sh:1722-1733
- **Concern**: Finding 1 [correctness]: the new unclosed-fence test explicitly waives the removed-count assertion, so the stdout protocol is not checked on the new unmatched-opener path.. Scenario: The existing section-aware test checks the balanced-fence log, but a debug print or malformed stdout emitted only when pass 1 drops an unmatched opener would still let the proposed new test pass because it only checks duplicate survival.
- **Proposed resolution**: Assert the exact `dedup-sweep: removed 0 duplicate line(s) from plan.txt` line in the new unclosed-fence case, using a fixture with no removable duplicates outside `## Constraints`.

### FINDING_5:
- **Reviewer(s)**: Cursor-dyn-stdout-protocol-drift, Codex-dyn-stdout-protocol-drift
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: <TMPDIR>/plan.txt:50-54; skills/design/scripts/plan-review-loop.sh:500-573; skills/design/scripts/plan-review-loop.sh:1352-1354
- **Concern**: Finding 2 [risk-integration]: the failure-modes section says a Python heredoc failure crashes Step 3, but the real call site runs `_run_post_apply_pipeline` under `if !`, which disables `errexit` inside the function and lets an empty `dedup_removed` fall through to `${dedup_removed:-0}`.. Scenario: If the rewritten Python exits before `print(removed)`, the wrapper can log `removed 0`, move the temp file, and only fail later through emit/validation behavior; that is the exact stdout drift the plan is meant to avoid.
- **Proposed resolution**: Add a minimum wrapper guard around the Python assignment: capture rc, require `dedup_removed` to match `^[0-9]+$`, and return failure before `mv -f` when it does not; update the failure-mode text to match that observed shell behavior.

### FINDING_6:
- **Reviewer(s)**: Cursor-dyn-test-edge-gap
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:44-48
- **Concern**: Multiple-unbalanced-openers bullet assumes a multi-entry stack dropped at EOF, but the nested-fence bullet mandates push-only-when-stack-is-empty (single slot). Scenario: Implementer may push every opener and change pass-1 semantics for ```a then ```b without closers; diverges from current toggle at plan-review-loop.sh:526-533
- **Proposed resolution**: Align bullet 44 with bullet 48: only the first unmatched opener occupies the stack; a later ```b with non-empty suffix is a failed closer attempt, not a second stack entry

### FINDING_7:
- **Reviewer(s)**: Codex-dyn-test-edge-gap
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:25-30; skills/design/scripts/test-plan-review-loop.sh:1663-1665
- **Concern**: The new test assertion names $DDED even though the planned fixture lives under $TMP/unclosed-fence. Scenario: Implementer follows the plan literally and greps the prior section-aware fixture, so the new regression test fails or checks the wrong plan file
- **Proposed resolution**: Use a fresh fixture variable for $TMP/unclosed-fence and assert against that variable's plan.txt

### FINDING_8:
- **Reviewer(s)**: Codex-dyn-test-edge-gap
- **Severity**: latent
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:47-59; skills/design/scripts/plan-review-loop.sh:522-533; skills/design/scripts/test-plan-review-loop.sh:1682-1745
- **Concern**: The plan specifies mismatched-tick and nested-looking fence semantics, but the new test covers only the basic unclosed-fence path and the existing section-aware test only incidentally covers ordinary balanced and language-tagged fences. Scenario: A stack rewrite that treats a smaller-tick line as a closer, or pushes a longer nested-looking marker instead of applying the existing closer rule, can pass the planned tests while changing balanced-fence behavior
- **Proposed resolution**: Keep the SIMPLE scope explicit: either add a brief coverage note that mismatched-tick and nested-looking cases are intentionally untested accepted risk, or fold one minimal assertion into the existing section-aware fixture to pin those two closer-rule cases
