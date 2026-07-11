### FINDING_1: Live identity check is inverted
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Codex-Pragmatic, Codex-Requirements
- **Severity**: major
- **Concern**: The live-row branch rejects identity-matched work as `active-stale-identity-mismatch`, even though matching live work must be rejoined. This breaks valid live rejoin and can cause duplicate launches.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Rename that bullet to identity-mismatched live row; keep the preceding rejoin bullet for identity-matched live rows with bgjob wait --max-wait-s 0
  - From Codex-Arch: Change this branch to test for an identity-mismatched live row. Keep identity-matched live rows on the rejoin-and-wait path.
  - From Codex-Pragmatic: Change line 112 to identity-mismatched live row, consistent with the approach, harness cases, and acceptance contract.
  - From Codex-Requirements: Change the stale-row directive to identity-mismatched. For an identity-matching live row, use the zero-duration wait only as the rejoin probe, then continue the adapter-owned chunked wait loop until `DONE` and emit the validated terminal envelope.


### FINDING_2: Live rejoin must own the blocking wait and retry loop
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Codex-Requirements
- **Severity**: major
- **Concern**: A live rejoin that performs `bgjob wait --max-wait-s 0` and exits does not observe completion, validate the terminal result, or own the required retry path. A `WAIT`, timeout, failed result, or invalid output can therefore escape the adapter contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Use `--max-wait-s 0` only as the initial rejoin probe. Continue with the documented repeated wait-until-DONE loop, validate the result, and route retryable failures through the same attempt-2 logic as a fresh launch.
  - From Codex-Innovation: Use zero-duration wait only as an immediate rejoin probe, then repeat the identical wait command until `DONE` or `DEAD`, validate the final envelope, and run the adapter-owned retry loop. Explicitly define this behavior for both live rejoin and fresh launches
  - From Codex-Requirements: Change the stale-row directive to identity-mismatched. For an identity-matching live row, use the zero-duration wait only as the rejoin probe, then continue the adapter-owned chunked wait loop until `DONE` and emit the validated terminal envelope.


### FINDING_4: Establish the Python import environment
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: major
- **Concern**: The inline fingerprint helper must import Piece 2's `architectural_assessment` helpers, but the adapter contract does not establish `PYTHONPATH` or an equivalent `sys.path` setup. The helper can therefore fail at runtime before launch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add rehydrate_plugin_root plus export PYTHONPATH="$CLAUDE_PLUGIN_ROOT/python${PYTHONPATH:+:$PYTHONPATH}" before any inline Python or cli.py call that imports larch.implement.architectural_assessment; document the requirement in step-8-assessment.md.
  - From Cursor-Pragmatic: Add export PYTHONPATH="$CLAUDE_PLUGIN_ROOT/python${PYTHONPATH:+:$PYTHONPATH}" after plugin-root rehydration, or require sys.path.insert(0, ...) in the inline helper, matching established Step 8 launcher patterns.


### FINDING_7: Launch the assessment wrapper as the bgjob child
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Concern**: The foreground adapter must start the Bash child wrapper so that the child owns stdout validation and translation into canonical `ASSESSMENT_*` result KVs. Starting the architectural-assessment CLI directly would bypass that envelope and undermine rejoin validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Document and implement bgjob start exactly like step-8-ship.sh: `-- bash "$SCRIPT_DIR/step-8-assessment.sh" --bgjob-child --merge-result-env "$MERGE_RESULT_ENV"`. Keep architectural-assessment run invocation inside child mode only.


