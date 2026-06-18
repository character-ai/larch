### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-clarify.sh:78-97
- **Concern**: python/clarify.py (planned _load_route_state_repo). Scenario: Missing route-state sidecar must not become route-state-read-failed
- **Proposed resolution**: Bash returns 0 when REPO is unset and `.design-step0-route-state.env` is absent; only a present file with a failed read yields route-state-read-failed. Calling `phase_driver_read_result_env` on a missing path raises OSError and can be misclassified as a hard clarify failure. Match `load_route_state_repo_fallback`: if REPO is already set, skip; if the sidecar is missing, continue with empty REPO; only when the file exists and allowlisted read fails, emit route-state-read-failed (fetch stages, publish does not).

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/clarify.py:design_clarify_main (fetch phase)
- **Concern**: Fetch phase calls clarify_state/clarify_comment_fetch in-process but still lists state-read-failed and fetch-read-failed tokens that only existed for subprocess stdout KV parse failures in design-clarify.sh:219-268. Scenario: An implementer may fabricate parse-failure branches or emit the wrong CLARIFY_FETCH_STATUS for ShipError/validation failures; Step 0b Final-summary routing and test_clarify.py token tables diverge from real Bash parity
- **Proposed resolution**: Add an explicit direct-call mapping table: gh/runtime errors and non-zero equivalents → state-failed/fetch-failed; wrong ClarifyState → unexpected-state; drop state-read-failed/fetch-read-failed from the Python fetch path (or document them as unreachable legacy tokens only)

### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/test-design-clarify.sh:198
- **Concern**: python/test_clarify.py (proposed). Scenario: Omitting the empty-SESSION_ID operator warning drops a contract the current harness enforces
- **Proposed resolution**: Current test-design-clarify.sh requires publish stdout to contain SESSION_ID missing (line 198). Bash prints **⚠ /design: SESSION_ID missing; skipping design log publish**. Plan moves publish behavior to Python tests but only says empty SESSION_ID skips publish/rename; it never requires preserving that warning. Shell harness scope also drops this assertion. Add the warning to the Python publish contract and test list (assert stdout contains SESSION_ID missing). If the shell harness no longer covers publish, drop line 198 only after the Python test owns the check.

### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/clarify.py (proposed; plan Approach lines 56-63)
- **Concern**: Plan does not define session-env merge order with inherited wrapper exports. Scenario: Plan loads only via design_lifecycle._load_source_env. When --session-env-path is a symlink and --claude-pid is absent, _load_source_env returns {} by design, but the thin wrapper still sources session env and exports DESIGN_TMPDIR/SESSION_ID before exec. A Python driver that reads only the load dict can fail DESIGN_TMPDIR required even though the child environment is valid.
- **Proposed resolution**: Before validation, build env from allowlisted os.environ keys, then update from _load_source_env (session file wins). Reuse design_lifecycle._require_design_tmpdir(env) for absolute/resolve() checks instead of ad-hoc validation.

### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/clarify.py (proposed; plan Fetch lines 88-117, test_clarify.py lines 173-174)
- **Concern**: Direct clarify_state/clarify_comment_fetch calls leave state-read-failed and fetch-read-failed semantics undefined. Scenario: Plan mandates in-process primitives, but those two tokens only existed when read-result-env parsing of subprocess stdout failed. Tests still require every fetch failure token including state-read-failed and fetch-read-failed. The plan does not say when the Python driver emits them.
- **Proposed resolution**: Add an explicit token map for the direct-call driver (e.g. which exception or internal parse failure maps to each CLARIFY_FETCH_STATUS). If no live path should emit -read-failed tokens anymore, narrow the wire contract and tests together; do not leave ambiguous.

### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/clarify.py (proposed; plan Publish lines 119-127)
- **Concern**: Publish request-state read does not pin the listed _read_result_env helper. Scenario: Bash publish reads .design-clarify-request.env through read-result-env.sh with a fixed allowlist and symlink refusal (design-clarify.sh:295-300). Plan lists _read_result_env but the publish steps only say Read the file, so an implementer could use a naive parser that follows symlinks or ingests unexpected keys.
- **Proposed resolution**: Require publish to load request state via _read_result_env wrapping design_lifecycle.phase_driver_read_result_env with allowlist REQUEST_ID REQUEST_BODY_FILE PLAN_FILE RESPONSE_FILE ISSUE_NUMBER REPO; on failure write CLARIFY_PUBLISH_STATUS=missing-request-state and exit 1.

### FINDING_7:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/clarify.py:119-153
- **Concern**: `_read_result_env` is listed but its publish-phase contract is unspecified while `_write_result_env` is fully specified. Scenario: Publish may read `.design-clarify-request.env` with a naive parser that follows symlinks, accepts non-allowlisted keys, or ignores CR/LF trust rules; Bash uses `read-result-env.sh` allowlisting via `read_safe_env`
- **Proposed resolution**: Bind `_read_result_env` to `design_lifecycle.phase_driver_read_result_env` (or equivalent) with an explicit allowlist (`REQUEST_ID`, `REQUEST_BODY_FILE`, `PLAN_FILE`, `RESPONSE_FILE`, `ISSUE_NUMBER`, `REPO`); refuse symlink/non-regular inputs; map read failures to `CLARIFY_PUBLISH_STATUS=missing-request-state` like current Bash

### FINDING_8:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: security
- **Location**: skills/design/scripts/design-clarify.sh (plan.txt:238-240)
- **Concern**: [SCOPE-REDUCTION] Wrapper still sources --session-env-path and requires DESIGN_TMPDIR before delegating. Scenario: The plan requires Python trusted symlink handling, but shell sourcing can execute an untrusted session env target and override CLAUDE_PLUGIN_ROOT before python/cli.py design clarify runs
- **Proposed resolution**: Remove wrapper session-env sourcing and DESIGN_TMPDIR validation; compute CLAUDE_PLUGIN_ROOT from launcher env or SCRIPT_DIR, forward --session-env-path and --claude-pid, and update the wrapper harness to assert Python owns session env loading
