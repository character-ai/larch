### FINDING_1: Publish-phase route-state failure must not stage failed-clarify
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: Route-state read failure handling must differ by phase. Today Bash only calls `stage_failed_clarify` on fetch-phase route-state failure; publish writes `CLARIFY_PUBLISH_STATUS=route-state-read-failed` and exits without staging. The port plan groups route-state handling with fetch staging and does not split behavior by phase, which could spuriously stage terminal failed-clarify state on publish when `REPO` is missing and `.design-step0-route-state.env` is unreadable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: A publish run with missing `REPO` and unreadable `.design-step0-route-state.env` could spuriously stage terminal failed-clarify state.


### FINDING_2: Publish path must validate REQUEST_ID before any side effects
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: The proposed publish path does not explicitly require a valid `REQUEST_ID` before side effects. A malformed `.design-clarify-request.env` could reach plan write or log publish before `clarify_comment_post` rejects the bad id, regressing the current fail-closed ordering in `design-clarify.sh` (where `validate_positive_int REQUEST_ID` runs at line 311 before redaction and plan write).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add an early positive-integer REQUEST_ID validation immediately after request-state load and before artifact redaction, plan write, log publish, response post, or label removal


### FINDING_3: Thin wrapper must validate argv before pause-save
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The thin-wrapper plan may drop argv validation before the pause-save branch. The current driver rejects missing or invalid `--issue` and `--phase` before pause-save (lines 167–174 precede the `.pause-requested` check at 204–206). A wrapper that runs pause-save first could accept empty `ISSUE` or skip phase checks, changing exit codes and pause-save inputs versus today.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Keep current ordering: parse and validate --phase and --issue (and --claude-pid when present) before the .pause-requested branch; only then exec design pause-save or delegate to python/cli.py design clarify


### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/clarify.py (proposed publish redaction); python/redact.py:417-445
- **Concern**: [SCOPE-REDUCTION] Publish redaction switches from secrets-only redaction to full path redaction. Scenario: The current shell uses python/cli.py redact secrets, which preserves tmpdir and operator paths; redact.redact() also rewrites paths and can change the published plan block during a parity port
- **Proposed resolution**: Use redact.redact_secrets_only() or the exact redact secrets equivalent, while keeping the empty-output and truncation-sentinel checks


### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/clarify.py:79-81
- **Concern**: [SCOPE-REDUCTION] Publish redaction calls redact.redact() instead of the bash parity surface redact secrets / redact_secrets_only(). Scenario: Bash pipes the plan through python/cli.py redact secrets (secrets-only). redact() also strips session tmpdir literals, so ported publish can rewrite plan paths/content differently and change the larch:plan block written to the issue
- **Proposed resolution**: Use redact_secrets_only() (or subprocess python/cli.py redact secrets) and keep the existing empty-file / non-zero exit checks only


### FINDING_6:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/clarify.py:planned publish redaction; python/redact.py:319-334
- **Concern**: [SCOPE-REDUCTION] Redaction plan switches from secrets-only parity to broader tmpdir redaction and new truncation-fail behavior. Scenario: Current design-clarify.sh uses python/cli.py redact secrets, which maps to redact_secrets_only and preserves tmpdir/operator paths. The planned redact.redact() rewrites those paths, and the new truncation-sentinel failure can reject a clarify plan the existing phase would publish. This is a behavior change in a parity port.
- **Proposed resolution**: Use redact.redact_secrets_only() for the plan block, and keep the existing redact command semantics unless a separate issue explicitly changes clarify redaction policy.


### FINDING_7:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/design-clarify.sh:189-205
- **Concern**: [SCOPE-REDUCTION] Wrapper owns pause-save before the Python route-state fallback. Scenario: The current script loads .design-step0-route-state.env before pause-save, so pause gets the resolved REPO when source-env lacks it. The planned wrapper pause branch runs before the Python driver can load route state, so a clarify pause can omit --repo and fall back to gh repo resolution against the wrong or unavailable repo.
- **Proposed resolution**: Remove the wrapper pause short-circuit and delegate to python/cli.py design clarify so the Python driver loads route state before pause-save, or load the same route-state fallback in the wrapper before invoking pause-save.



### FINDING_2: Thin wrapper must not exec with consumed `"$@"`
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: blocking
- **Concern**: The planned `design-clarify.sh` thin wrapper parses `--session-env-path`, `--claude-pid`, `--phase`, and `--issue` in a `while`/`case` loop that shifts every flag off `"$@"`. If `exec python3 ... design clarify "$@"` runs after that loop, Python receives no flags and cannot run either fetch or publish phase.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Save delegation argv before parsing (ORIGINAL_ARGV=("$@") at top, or rebuild _delegate_args like design-step5.sh) and exec with that saved array; align test-design-clarify.sh with the chosen contract
  - From Cursor-Pragmatic: After validation, exec with explicit reconstructed flags only, e.g. optional --session-env-path / --claude-pid plus required --phase "$PHASE" --issue "$ISSUE". Match the harness contract that forwards those four flags.


### FINDING_3: Pause-save path must terminate before clarify phase work
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The planned shared startup in `python/clarify.py` honors `.pause-requested` but does not stop the driver afterward. Bash uses `exec` into `design pause-save`, so fetch/publish never run. A direct `pause_save_main()` call that returns 0 would fall through into clarify work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: On .pause-requested, call pause_save_main (or CLI equivalent), emit its KVs, and return immediately without fetch/publish. Add an explicit test that clarify primitives are not invoked after pause.


### FINDING_4: Invalid REQUEST_ID failure contract must match Bash
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Parity for invalid `REQUEST_ID` is unspecified in the plan. Bash `validate_positive_int` on `REQUEST_ID` (`design-clarify.sh:311`) calls `fail()` and exits 2 without writing `.design-clarify-publish-result.env`. Other publish failures write that file and exit 1. The plan/tests only say "fails closed before redaction" and do not pin env write or exit code.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Omit publish result env on invalid REQUEST_ID and exit 2, matching Bash. Or document a deliberate behavior change and update SKILL.md consumers.




### FINDING_2: Fetch failure paths omit SUMMARY_OUTCOME=failed-clarify
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Fetch failure paths omit `SUMMARY_OUTCOME=failed-clarify` in the ported contract. Bash always writes and emits `SUMMARY_OUTCOME=failed-clarify` on every fetch failure; SKILL Step 0b exports `SUMMARY_OUTCOME=failed-clarify` on non-zero fetch. Omitting it breaks Final-summary routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Require `SUMMARY_OUTCOME=failed-clarify` in every fetch failure `.design-clarify-fetch-result.env` write and matching stdout KV for all `CLARIFY_FETCH_STATUS` failure tokens.


### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: security
- **Location**: python/clarify.py:50-73
- **Concern**: [SCOPE-REDUCTION] Planned `_load_session_env_file` reimplements session-env parsing without trusted symlink handling. Scenario: The launcher always passes `--session-env-path` to `current-design-env-$PPID.sh` (a symlink). `design_lifecycle._load_source_env` returns `{}` for symlinks unless `--claude-pid` drives `session_env.resolve_trusted_design_session_env_source`. A naive parser can miss `DESIGN_TMPDIR`/`SESSION_ID` on the Python path or read an untrusted symlink target
- **Proposed resolution**: Reuse `design_lifecycle._load_source_env(path, CLARIFY_ENV_ALLOW, claude_pid=parsed_claude_pid)` instead of a new parser; keep the existing allowlisted key set




### FINDING_1: `_write_result_env` lacks Bash `write_result_env` trust-boundary parity
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The plan pins symlink refusal for reads but does not specify equivalent write-side guarantees for `_write_result_env`. A naive Python writer (as in `design_postplan._write_result_env`) can write through a symlinked `.design-clarify-*-result.env`, accept CR/LF in values, or leave a partially written file on crash. That weakens the clarify result-env trust boundary Bash enforces today via `write_result_env` in `design-clarify.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Specify `_write_result_env` parity: refuse symlink destination paths, reject values containing CR/LF, and use temp-then-rename atomic write before emitting stdout KVs.




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



