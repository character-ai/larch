### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-step2-dispatch.sh:752-779
- **Concern**: Test 16 still writes and asserts qa-pending at session-tmpdir root. Scenario: Plan only retargets STEP2_MANIFEST_PATH for test 16; stub still writes $IMPLEMENT_TMPDIR/qa-pending.json and QA_PENDING_16=$TMP16/qa-pending.json while codex path sets QA_PENDING_PATH=$TMPDIR_ARG/codex-step2-out/qa-pending.json — repair reads empty path → STATUS=bailed (qa-pending-missing/manifest-schema-invalid) and harness fails
- **Proposed resolution**: In test 16 stub: write qa-pending under $IMPDIR/codex-step2-out/ (or derive from STEP2_MANIFEST_PATH dirname); set QA_PENDING_16=$TMP16/codex-step2-out/qa-pending.json

### FINDING_2:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md:105
- **Concern**: Plan omits SECURITY.md update while narrowing Codex Step 2 --add-dir. Scenario: After landing, SECURITY.md still tells operators the full dispatcher session tmpdir is Codex-writable and documents the pre-narrowing trust boundary; security reviewers and operators can mis-scope tamperable artifacts (e.g. session-env.sh, plan copies) relative to shipped behavior
- **Proposed resolution**: Add a minimal SECURITY.md edit in the plan: Codex implementer --add-dir is limited to codex-step2-out/ (dirname of manifest/qa/transcript), not all of IMPLEMENT_TMPDIR; orchestrator-owned files outside that subdir are outside the Codex write grant

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-codex-implementer.sh:344
- **Concern**: Proposed new harness case labeled test 4b collides with existing fail 4b. Scenario: Harness already uses fail 4b for CODEX_HOME outside IMPLEMENT_TMPDIR; adding a transcript-parent test as 4b breaks pass/fail numbering or overwrites the wrong assertion
- **Proposed resolution**: Name the new transcript-directory case 11c (after parent-mismatch test 11) or another unused id; keep fail 4b for the CODEX_HOME check only

### FINDING_4:
- **Reviewer(s)**: Cursor-dyn-harness-table-completeness
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-step2-dispatch.sh:753-756,779
- **Concern**: Test 16 codex stub and post-run assertion still use tmpdir-root qa-pending.json; plan table only retargets STEP2_MANIFEST_PATH for test 16. Scenario: After CODER=codex moves QA_PENDING_PATH to $TMPDIR/codex-step2-out/qa-pending.json, stub writes items[] to $IMPLEMENT_TMPDIR/qa-pending.json and assertion reads $TMP16/qa-pending.json; dispatcher repair reads the subdir path and sees missing/wrong file → test 16 fails (qa-pending-missing or wrong STATUS) despite table listing test 16
- **Proposed resolution**: Extend the test-step2-dispatch.sh plan for test 16: stub writes to $IMPLEMENT_TMPDIR/codex-step2-out/qa-pending.json (or dirname of STEP2_MANIFEST_PATH); set QA_PENDING_16=$TMP16/codex-step2-out/qa-pending.json

### FINDING_5:
- **Reviewer(s)**: Cursor-dyn-split-dependency-isolation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/launch-codex-implement.md:14
- **Concern**: Planned sibling edit only removes the Codex-writable sentence and adds a subdir note; it leaves "The granted directory is the ENTIRE session tmpdir" and dispatcher-tmpdir-wide framing that contradicts narrowed `SESSION_TMPDIR`. Scenario: An operator reading only `launch-codex-implement.md` still believes baseline files, sidecars, and other `$IMPLEMENT_TMPDIR` artifacts are inside the `--add-dir` grant
- **Proposed resolution**: Rewrite the whole `--add-dir` invariant bullet: `SESSION_TMPDIR` is `dirname("$MANIFEST_PATH")` (on the codex path, `$IMPLEMENT_TMPDIR/codex-step2-out/`); only manifest, qa-pending, and transcript live there; other tmpdir artifacts are launcher-written and outside the grant. Drop "ENTIRE session tmpdir" and the Codex-writable list
