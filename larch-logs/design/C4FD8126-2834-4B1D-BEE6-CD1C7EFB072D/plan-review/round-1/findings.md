### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/scripts/step2-implement.sh:152-260
- **Concern**: Manifest/qa/transcript paths move under codex-step2-out for every external implementer. Scenario: Plan sets STEP2_OUT_DIR after TMPDIR_ARG canonicalization and rewrites MANIFEST_PATH/QA_PENDING_PATH/TRANSCRIPT_PATH in the shared block after the codex/cursor case — Cursor Step 2 would write into a Codex-named subdir without needing sandbox narrowing
- **Proposed resolution**: Scope mkdir and the three path variables to CODER=codex only (e.g. set defaults in the shared block; override inside the codex) branch); leave Cursor paths at $TMPDIR_ARG/manifest.json etc.

### FINDING_2:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/scripts/step2-implement.sh:152-260
- **Concern**: Codex subdir relocation is unconditional and mkdir runs before claude early-exit. Scenario: Plan inserts mkdir and retargets MANIFEST_PATH/QA_PENDING_PATH/TRANSCRIPT_PATH for every external implementer (including Cursor) and even claude_fallback runs that exit at line 176; that is scope creep beyond narrowing Codex --add-dir and will break Cursor stub tests (e.g. test 3e) unless every cursor harness path is also rewritten
- **Proposed resolution**: Gate STEP2_OUT_DIR/mkdir and the three Codex output paths on CODER=codex only; leave Cursor paths at $TMPDIR_ARG/... and place mkdir after the claude/cursor-unhealthy early returns

### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-step2-dispatch.sh:540-1857
- **Concern**: Plan updates STEP2_MANIFEST_PATH only for tests 17a–17c. Scenario: ~15 other codex dispatch tests still set STEP2_MANIFEST_PATH to $TMP/manifest.json while step2-implement.sh will expect $TMP/codex-step2-out/manifest.json; stubs write the wrong file → manifest-missing / wrong STATUS (12a/12b, 13, 16, 18, M1, M2, M12, M16–M19, 25, etc.)
- **Proposed resolution**: Set STEP2_MANIFEST_PATH to $TMP/codex-step2-out/manifest.json (or derive from dispatcher layout) for every codex stub invocation; keep 17a–17c META path updates already listed
