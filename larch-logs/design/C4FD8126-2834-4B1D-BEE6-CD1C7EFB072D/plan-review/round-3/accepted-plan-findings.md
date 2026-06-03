### FINDING_1: Codex path block must follow shared path defaults
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: The plan says to insert the `CODER=codex` subdir block right after the `case "$CODER"` block, but `MANIFEST_PATH`, `QA_PENDING_PATH`, and `TRANSCRIPT_PATH` are not assigned until lines 256–259. If an implementer follows the plan literally and adds the gated block immediately after line 244, the block assigns to variables that do not exist yet (or runs before shared defaults), which can break the codex path at runtime or on the first `/implement` with `--coder=codex`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Clarify in the plan: keep lines 256-259 as shared defaults, then place the `if [[ "$CODER" == "codex" ]]` block immediately after line 259 (before `SIDECAR_LOG` / agent-prompt checks), retargeting only the three Codex-written paths


### FINDING_2: Outcomes bullet still documents root-level manifest for codex
- **Reviewer(s)**: Cursor-dyn-stale-reader-sweep
- **Severity**: important
- **Concern**: The Outcomes bullet on line 69 still says the canonical manifest lives at `$TMPDIR/manifest.json`. If the plan updates lines 12–13 for the codex subdir layout but leaves line 69 unqualified, operators reading Outcomes will assume the codex manifest stays at the tmpdir root after the change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-stale-reader-sweep: On the same UPDATED step2-implement.md edit, qualify line 69: codex complete path uses $TMPDIR/codex-step2-out/manifest.json (or $MANIFEST_PATH); cursor unchanged at tmpdir root

