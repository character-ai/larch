### FINDING_1:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/step2-implement.sh:224-260
- **Concern**: Plan says to insert the `CODER=codex` subdir block right after the `case "$CODER"` block, but `MANIFEST_PATH` / `QA_PENDING_PATH` / `TRANSCRIPT_PATH` are not assigned until lines 256-259. Scenario: An implementer following the plan literally adds the gated block immediately after line 244; the block assigns to variables that do not exist yet (or runs before shared defaults), breaking the codex path at runtime or on first `/implement` with `--coder=codex`
- **Proposed resolution**: Clarify in the plan: keep lines 256-259 as shared defaults, then place the `if [[ "$CODER" == "codex" ]]` block immediately after line 259 (before `SIDECAR_LOG` / agent-prompt checks), retargeting only the three Codex-written paths

### FINDING_2:
- **Reviewer(s)**: Cursor-dyn-stale-reader-sweep
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/step2-implement.md:69
- **Concern**: Outcome bullet still says canonical manifest lives at $TMPDIR/manifest.json. Scenario: Plan updates lines 12-13 for codex subdir layout but leaves line 69 unqualified; operators reading Outcomes think codex manifest stays at tmpdir root after the change
- **Proposed resolution**: On the same UPDATED step2-implement.md edit, qualify line 69: codex complete path uses $TMPDIR/codex-step2-out/manifest.json (or $MANIFEST_PATH); cursor unchanged at tmpdir root
