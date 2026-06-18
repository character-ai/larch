### FINDING_1: Missing route-state sidecar must not emit route-state-read-failed
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The planned `_load_route_state_repo` helper must mirror Bash `load_route_state_repo_fallback`: if `REPO` is already set, skip; if `.design-step0-route-state.env` is absent, continue with empty `REPO`; only when the file exists and an allowlisted read fails should fetch emit `route-state-read-failed` (publish does not use this path). Calling `phase_driver_read_result_env` on a missing path raises `OSError` and can be misclassified as a hard clarify failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Bash returns 0 when REPO is unset and `.design-step0-route-state.env` is absent; only a present file with a failed read yields route-state-read-failed. Calling `phase_driver_read_result_env` on a missing path raises OSError and can be misclassified as a hard clarify failure. Match `load_route_state_repo_fallback`: if REPO is already set, skip; if the sidecar is missing, continue with empty REPO; only when the file exists and allowlisted read fails, emit route-state-read-failed (fetch stages, publish does not).


### FINDING_2: Fetch-phase CLARIFY_FETCH_STATUS tokens undefined for in-process calls
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan ports fetch to direct `clarify_state()` / `clarify_comment_fetch()` calls, but `state-read-failed` and `fetch-read-failed` only existed for subprocess stdout KV parse failures in `design-clarify.sh:219-268`. Without an explicit direct-call mapping (or a deliberate contract narrowing), implementers may fabricate parse-failure branches, emit wrong `CLARIFY_FETCH_STATUS` values for `ShipError`/validation failures, or leave `test_clarify.py` token tables divergent from real Bash parity and Step 0b Final-summary routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add an explicit direct-call mapping table: gh/runtime errors and non-zero equivalents → state-failed/fetch-failed; wrong ClarifyState → unexpected-state; drop state-read-failed/fetch-read-failed from the Python fetch path (or document them as unreachable legacy tokens only)
  - From Cursor-Pragmatic: Add an explicit token map for the direct-call driver (e.g. which exception or internal parse failure maps to each CLARIFY_FETCH_STATUS). If no live path should emit -read-failed tokens anymore, narrow the wire contract and tests together; do not leave ambiguous.


### FINDING_4: Session-env merge order with inherited wrapper exports unspecified
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan loads env only via `design_lifecycle._load_source_env`. When `--session-env-path` is a symlink and `--claude-pid` is absent, `_load_source_env` returns `{}` by design, but the thin wrapper still sources session env and exports `DESIGN_TMPDIR`/`SESSION_ID` before exec. A Python driver that reads only the load dict can fail `DESIGN_TMPDIR required` even though the child environment is valid.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Before validation, build env from allowlisted os.environ keys, then update from _load_source_env (session file wins). Reuse design_lifecycle._require_design_tmpdir(env) for absolute/resolve() checks instead of ad-hoc validation.


### FINDING_5: Publish request-state read must pin `_read_result_env` allowlist contract
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: `_read_result_env` is listed in the plan but its publish-phase contract is unspecified while `_write_result_env` is fully specified. Bash publish reads `.design-clarify-request.env` through `read-result-env.sh` with a fixed allowlist and symlink refusal (`design-clarify.sh:295-300`). Without binding the helper, an implementer could use a naive parser that follows symlinks, accepts non-allowlisted keys, or ignores CR/LF trust rules.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Require publish to load request state via _read_result_env wrapping design_lifecycle.phase_driver_read_result_env with allowlist REQUEST_ID REQUEST_BODY_FILE PLAN_FILE RESPONSE_FILE ISSUE_NUMBER REPO; on failure write CLARIFY_PUBLISH_STATUS=missing-request-state and exit 1.
  - From Cursor-Requirements: Bind `_read_result_env` to `design_lifecycle.phase_driver_read_result_env` (or equivalent) with an explicit allowlist (`REQUEST_ID`, `REQUEST_BODY_FILE`, `PLAN_FILE`, `RESPONSE_FILE`, `ISSUE_NUMBER`, `REPO`); refuse symlink/non-regular inputs; map read failures to `CLARIFY_PUBLISH_STATUS=missing-request-state` like current Bash


