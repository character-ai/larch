### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/implement/scripts/step-8-assessment.sh
- **Concern**: The script spec says exit 2 on an identity-matched live registry row. Scenario: A implementer following the script bullets would treat every valid identity-matched live row as active-stale-identity-mismatch and refuse rejoin; live work could never be reused and fresh launches would always fail while the prior child is still running
- **Proposed resolution**: Rename that bullet to identity-mismatched live row; keep the preceding rejoin bullet for identity-matched live rows with bgjob wait --max-wait-s 0

### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/implement/scripts/step-8-assessment.sh:112-113
- **Concern**: The live-row branch contradicts the identity rules: it says an identity-matched live row must emit active-stale-identity-mismatch, while the surrounding contract requires matched live work to rejoin.. Scenario: A valid matching live job is rejected instead of rejoined, violating the live-rejoin acceptance case and potentially causing a duplicate launch by the caller.
- **Proposed resolution**: Change this branch to test for an identity-mismatched live row. Keep identity-matched live rows on the rejoin-and-wait path.

### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/implement/scripts/step-8-assessment.sh:110,121-127
- **Concern**: The live-rejoin path calls `bgjob wait --max-wait-s 0` and exits, but the adapter is also defined as the owner of waiting, validation, and the single retry.. Scenario: If the probe returns `BGJOB_STATUS=WAIT`, this invocation stops observing the job. If the job later fails or produces invalid output, no specified owner performs attempt 2.
- **Proposed resolution**: Use `--max-wait-s 0` only as the initial rejoin probe. Continue with the documented repeated wait-until-DONE loop, validate the result, and route retryable failures through the same attempt-2 logic as a fresh launch.

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/step-8-assessment.sh:registry-live-check
- **Concern**: Registry child/daemon liveness predicate is unspecified. Scenario: The plan says to use established registry helpers but does not pin whether a row is live when child OR daemon is live (step-8-ship.sh) or when both are live (step-5-review.sh). Step 8 siblings disagree. Wrong choice can unlink a registry row while a child is still running and start duplicate assessment work, or skip needed active-stale handling.
- **Proposed resolution**: Pin step-8-ship.sh semantics: treat the row as live if child_liveness OR daemon_liveness is true; only unlink dead rows without a completed result env; on live row with identity mismatch emit ASSESSMENT_ERROR=active-stale-identity-mismatch and exit 2.

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: skills/implement/scripts/step-8-assessment.sh:python-import-setup
- **Concern**: Piece 2 import setup is missing from the adapter contract. Scenario: The shared fingerprint helper must import normalize_kinds and validate_materialization from python/larch/implement/architectural_assessment.py. step-8-ship.sh exports PYTHONPATH="$CLAUDE_PLUGIN_ROOT/python" before inline Python, but the plan never requires that for step-8-assessment.sh. Without it, launch-time fingerprint computation can fail at runtime despite passing bash -n and ShellCheck.
- **Proposed resolution**: Add rehydrate_plugin_root plus export PYTHONPATH="$CLAUDE_PLUGIN_ROOT/python${PYTHONPATH:+:$PYTHONPATH}" before any inline Python or cli.py call that imports larch.implement.architectural_assessment; document the requirement in step-8-assessment.md.

### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: skills/implement/scripts/step-8-assessment.sh:handoff-kind-parse
- **Concern**: Duplicate kind rejection is listed in edge cases but not wired in the script steps. Scenario: Approach item 2 says reject duplicate tokens, but the same bullet also delegates deduplication to normalize_kinds, which silently dedupes per python/tests/implement/test_architectural_assessment.py. Edge cases require failure on repeated DETAIL tokens; the script bullets jump straight to normalize_kinds with no pre-check. The adapter can accept invariants,invariants, publish a deduped ASSESSMENT_REQUESTED_KINDS, and diverge from the assessments handoff Tool Failure contract Piece 4 expects.
- **Proposed resolution**: Before normalize_kinds, split DETAIL or DETAIL_FILE on commas, trim tokens, and exit 2 on empty, unknown, or duplicate tokens; call normalize_kinds only after that scan passes; add a harness case for repeated tokens.

### FINDING_9:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: plan.txt:109-127
- **Concern**: Live rejoin uses `bgjob wait --max-wait-s 0` and then exits, which conflicts with the adapter's blocking foreground contract and the required retry owner. Scenario: If the matching row is still running, zero-duration wait returns `BGJOB_STATUS=WAIT`. Exiting at that point hands control back without validating completion or owning the retry loop. Piece 4 may relaunch or continue without the required result, and a timeout or invalid child result will not receive the planned second attempt
- **Proposed resolution**: Use zero-duration wait only as an immediate rejoin probe, then repeat the identical wait command until `DONE` or `DEAD`, validate the final envelope, and run the adapter-owned retry loop. Explicitly define this behavior for both live rejoin and fresh launches

### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/implement/scripts/step-8-assessment.sh:repo-root
- **Concern**: Repo root source is not pinned to the session-env contract. Scenario: The plan says resolve repo root from persisted run state but never names the authoritative key or file. step-8-ci-fixer.sh reads REPO_ROOT from session-env.sh; ship-pr-state.sh only carries the GitHub slug REPO. An implementer can pass owner/repo to --repo-root, breaking validate_materialization git checks and assessment execution.
- **Proposed resolution**: Pin repo root to REPO_ROOT from $IMPLEMENT_TMPDIR/session-env.sh using the same read_key pattern as step-8-ci-fixer.sh, validate it is a non-symlink directory with .git, and pass that path to the fingerprint helper and architectural-assessment run.

### FINDING_11:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/implement/scripts/step-8-assessment.sh:python-imports
- **Concern**: Shared fingerprint helper lacks an explicit Python import surface. Scenario: The plan requires a bounded inline Python helper that imports Piece 2 normalize_kinds and validate_materialization, but the four-file scope includes no new Python module and the script section does not require PYTHONPATH or sys.path setup. step-8-ship.sh exports PYTHONPATH; registry helpers use sys.path.insert. Without one of these, the helper fails at import time and the adapter cannot compute ASSESSMENT_COVERED_FINGERPRINT or launch.
- **Proposed resolution**: Add export PYTHONPATH="$CLAUDE_PLUGIN_ROOT/python${PYTHONPATH:+:$PYTHONPATH}" after plugin-root rehydration, or require sys.path.insert(0, ...) in the inline helper, matching established Step 8 launcher patterns.

### FINDING_14:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: plan.txt:110-112
- **Concern**: Live-row instructions invert the identity check. Scenario: Line 110 requires rejoining an identity-matching live job, but line 112 requires the same identity-matching live job to fail with active-stale-identity-mismatch. An implementation following line 112 breaks the required live-rejoin path.
- **Proposed resolution**: Change line 112 to identity-mismatched live row, consistent with the approach, harness cases, and acceptance contract.

### FINDING_15:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/implement/scripts/step-8-assessment.sh:handoff-parse
- **Concern**: Handoff kind parsing must reject duplicate tokens before normalize_kinds. Scenario: Piece 2 normalize_kinds silently deduplicates repeats (test_normalize_kinds_deduplicates_and_orders). If the adapter passes raw handoff tokens straight through, DETAIL=invariants,invariants becomes a valid single-kind launch instead of the ship-route Tool Failure required by ship-pr-exit-matrix.md.
- **Proposed resolution**: In step-8-assessment.sh, pin the assessments handoff grammar from ship-pr-exit-matrix.md: read DETAIL then DETAIL_FILE fallback, split on commas, trim tokens, fail closed on empty/unknown/duplicate tokens, then call normalize_kinds only on the cleaned unique set. Add a harness case for duplicate-token rejection.

### FINDING_16:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: architecture
- **Location**: skills/implement/scripts/step-8-assessment.sh:bgjob-child
- **Concern**: Foreground launch must bgjob-start the bash child wrapper, not architectural-assessment run directly. Scenario: The child contract owns stdout validation and translation into ASSESSMENT_* merge-result KVs. Launching python/cli.py architectural-assessment run as the bgjob child would skip that envelope and break rejoin identity checks.
- **Proposed resolution**: Document and implement bgjob start exactly like step-8-ship.sh: `-- bash "$SCRIPT_DIR/step-8-assessment.sh" --bgjob-child --merge-result-env "$MERGE_RESULT_ENV"`. Keep architectural-assessment run invocation inside child mode only.

### FINDING_18:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/implement/scripts/step-8-assessment.sh:live-rejoin branch
- **Concern**: The live-rejoin directives conflict with each other and with the blocking foreground contract. Scenario: The plan first requires an identity-matching live row to use `bgjob wait --max-wait-s 0` and exit, which returns `BGJOB_STATUS=WAIT` while work remains live. It then directs the identity-matched live-row branch to fail with `active-stale-identity-mismatch`, although that error applies only to mismatched identity. Either implementation breaks required live rejoin by returning before canonical results exist or rejecting valid work.
- **Proposed resolution**: Change the stale-row directive to identity-mismatched. For an identity-matching live row, use the zero-duration wait only as the rejoin probe, then continue the adapter-owned chunked wait loop until `DONE` and emit the validated terminal envelope.
