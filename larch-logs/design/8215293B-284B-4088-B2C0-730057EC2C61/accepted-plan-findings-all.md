### FINDING_1: Bgjob timeout budget is unspecified or too low
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: The adapter does not pin a per-attempt `--budget-s` above Piece 2’s 1800-second assessment timeout. A too-low or ad hoc budget can terminate a healthy child, consume the retry, and produce a fail-closed result.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Pin `--budget-s` to at least 5400 (or another explicit margin above 1800) in the adapter and contract doc
  - From Cursor-Innovation: Pin `--budget-s` in the script spec and contract doc (for example 2100-2400s minimum, with rationale tied to the 1800s child timeout plus merge/finalize overhead), matching the explicit budget pins in `step-8-ship.sh` and `step-8-ci-fixer.sh`.
  - From Cursor-Pragmatic: Pin `--budget-s` in the script and contract doc to at least Piece 2's 1800s launcher budget plus modest child overhead (for example 1920-2100s), and add a harness static assert like test-step-8-ship.sh
  - From Cursor-Requirements: Pin `--budget-s` in step-8-assessment.sh and step-8-assessment.md to a value strictly greater than Piece 2's 1800s child timeout (for example 2100s or 2400s per attempt), matching the step-8-ship.sh pattern of explicit budget wiring


### FINDING_2: Covered-fingerprint and result-KV contracts are underspecified
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: major
- **Concern**: Live and completed rejoin depend on an exact requested-kind set and covered fingerprint, but the plan does not define a byte-stable serialization, hash algorithm, exact KV names, or allowed result-state grammars. The adapter, child, merge envelope, and harness could therefore disagree about identity or result validity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Define one canonical digest in step-8-assessment.md (ordered kinds plus HEAD_SHA, BASE_REF, DIFF_FINGERPRINT per kind, explicit separator rules) and implement it in the bounded Python helper and harness stubs
  - From Cursor-Innovation: Document exact KV names (for example `ASSESSMENT_REQUESTED_KINDS`, `ASSESSMENT_COVERED_FINGERPRINT`, `ASSESSMENT_STATUS`, `ASSESSMENT_ATTEMPT`) and the fingerprint serialization/hash contract in `step-8-assessment.md`; require one shared helper used for prelaunch, merge-result seeding, and post-child validation.
  - From Cursor-Pragmatic: Define one normative algorithm in the contract doc (ordered normalized kinds; per-kind HEAD_SHA, BASE_REF, DIFF_FINGERPRINT; unambiguous delimiter; single sha256 hex) and require the inline Python helper and harness to implement exactly that
  - From Cursor-Requirements: Add a normative fingerprint section to step-8-assessment.md: exact KV names (for example REQUESTED_KINDS and COVERED_FINGERPRINT), ordered per-kind tuple fields (kind, HEAD_SHA, BASE_REF, DIFF_FINGERPRINT), canonical serialization, and sha256 digest; require the inline Python helper and harness stubs to implement that grammar verbatim
  - From Codex-Requirements: Define the canonical result KVs and their exact grammars in the contract and harness plan, including requested-kind ordering, fingerprint format, completion states, attempt states, and per-kind result encoding


### FINDING_3: Post-run materialization equality can cause false failure
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: Requiring post-child materialization fingerprints to equal launch-time fingerprints conflicts with Piece 2’s refresh behavior. A valid assessment can update materialization while HEAD or incremental scope changes, causing a false retry and terminal fail-closed result.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Validate child stdout and per-kind coverage only; publish the launch-time covered fingerprint in merge/result KVs; do not fail success solely because post-run materialization files differ


### FINDING_6: The one-retry contract has no executable owner
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Concern**: The foreground adapter starts a bgjob and returns, while the child only performs one assessment attempt. If the child times out or emits invalid output, no specified process observes the failed result and launches attempt two, so the required retry and fail-closed fallback cannot occur.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Define where retry state is observed and executed. Either make the adapter wait and relaunch within the same invocation, or add an explicit re-entry/retry path that the caller invokes after reading the failed result. Specify how the second attempt preserves the current identity and terminal `BGJOB_RC`.


### FINDING_7: Mismatched live registry rows can collide with fresh launches
- **Reviewer(s)**: Codex-Arch, Codex-Innovation
- **Severity**: major
- **Concern**: A mismatched live row cannot safely be removed, but every attempt uses the fixed `implement-step8-assessment` slug. Starting fresh work can overwrite the registry while the old child or daemon remains live and untracked, causing duplicate or blocked assessment work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Refuse a fresh launch while a mismatched row has a live child or daemon, and return a distinct active-stale error for re-entry. Alternatively, use a collision-safe attempt identity and define validated termination and cleanup before starting the replacement.
  - From Codex-Innovation:


### FINDING_10: Child validation failures must produce non-zero exit status
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Concern**: The child could persist failure KVs and still exit zero, causing `BGJOB_RC=0`, skipping retry, and publishing false success. Usage errors, failed status, malformed or missing KVs, coverage mismatches, and identity drift need an explicit non-zero exit contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Document and implement explicit child non-zero exit on usage-error, failed status, malformed/missing KVs, kind-coverage mismatch, or post-run identity drift; reserve exit 0 only for fully validated success


### FINDING_12: Terminal fail-closed envelopes must be rejoinable
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Concern**: After retry exhaustion, a completed fail-closed envelope may have a non-zero `BGJOB_RC`. If completed rejoin requires `BGJOB_RC=0`, a resumed run can relaunch work instead of reusing the terminal result, potentially creating a third attempt.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Extend contract and harness: identity-matched completed envelopes with ASSESSMENT_STATUS=fail-closed are rejoinable via bgjob wait --max-wait-s 0 even when BGJOB_RC is non-zero; foreground must not start a third attempt


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


