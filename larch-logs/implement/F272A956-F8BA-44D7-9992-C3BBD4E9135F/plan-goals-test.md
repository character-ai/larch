## Goal
Implement issue #4674: [IMPLEMENTING] sh-to-py G6.1: Clarify phase port.

## Implementation Plan
## Plan

## Approach

Use direct repository inspection. `approach-synthesis` is `NO_SKETCHES`.

Port only the clarify phase driver.

Keep behavior stable:

- Preserve fetch and publish result env keys.
- Preserve clarify comment wire markers.
- Keep `design-clarify.sh` because `design-run-$PPID.sh` still launches by `.sh` filename.
- Keep `design-stage-terminal-state.sh` as a subprocess on **fetch-phase** hard failures only.
- Do not port other G6 scripts.

**Reviewer-driven parity fixes** (accepted findings):

- Split route-state failure handling by phase: fetch may stage `failed-clarify`; publish must not.
- **Missing route-state sidecar is not a failure**: mirror Bash `load_route_state_repo_fallback` — skip when `REPO` is already set; when `.design-step0-route-state.env` is absent, continue with empty `REPO`; emit `route-state-read-failed` only when the file **exists** and an allowlisted read fails.
- Publish must validate `REQUEST_ID` as a positive integer immediately after request-state load and before artifact checks, redaction, plan write, log publish, response post, or label removal.
- Invalid `REQUEST_ID` must match Bash `fail()` semantics: **do not** write `.design-clarify-publish-result.env`; emit a stderr error and **exit 2** (distinct from publish failures that write result env and exit 1).
- Wrapper must parse and validate `--phase`, `--issue`, and `--claude-pid` (when present) before delegating; wrapper must not own pause-save (Python loads route-state fallback first, then honors pause).
- Wrapper must **not** delegate with consumed `"$@"` after argv parsing; rebuild delegation argv explicitly (same `_delegate_args` pattern as `design-step5.sh`).
- Publish redaction must use secrets-only parity (`redact_secrets_only()` / `python/cli.py redact secrets`), not full `redact()` tmpdir rewriting.
- Pause-save must **terminate** the driver: on `.pause-requested`, call `pause_save_main` (or CLI equivalent), emit its KVs, and return immediately without fetch/publish work (Bash uses `exec` into pause-save).
- **Every live fetch failure** must write and emit `SUMMARY_OUTCOME=failed-clarify` alongside the `CLARIFY_FETCH_STATUS` failure token (Bash parity; required for Step 0b Final-summary routing).
- Session env merge must mirror wrapper+child parity: seed from allowlisted `os.environ`, then overlay `_load_source_env` (session file wins); use `design_lifecycle._require_design_tmpdir(env)` for absolute/existing directory checks.
- **`_write_result_env` must match Bash `write_result_env` trust boundaries**: refuse symlink destination paths, reject any value containing CR or LF, write via temp-then-rename atomic replace, and only emit stdout KVs after a successful rename.
- **`_read_result_env` must mirror Bash `read-result-env.sh` read-side trust boundaries** for publish request-state and route-state reads: wrap `design_lifecycle.phase_driver_read_result_env` with explicit allowlists, refuse symlink/non-regular inputs, map read failures to the same publish/fetch status tokens as Bash.

**Direct-call fetch token contract** (subprocess `-read-failed` tokens are Bash-only legacy; Python must not emit them):

| Condition | `CLARIFY_FETCH_STATUS` | Stage failed clarify? |
|---|---|---|
| Route sidecar present, allowlisted read fails | `route-state-read-failed` | fetch yes; publish no |
| `clarify_state` raises `ShipError` or other runtime/gh failure | `state-failed` | yes |
| `clarify_state` returns state != `awaiting-response` or empty `last_request_id` | `unexpected-state` | yes |
| `clarify_comment_fetch` raises `ShipError` or runtime/gh failure | `fetch-failed` | yes |
| `clarify_comment_fetch` raises `_ClarifyValidationError` | `fetch-failed` | yes |
| Success | `ok` | no |

Unreachable in the Python driver (document as legacy subprocess-only): `state-read-failed`, `fetch-read-failed`.

## Files to modify/create

### UPDATED: python/clarify.py

Add `design_clarify_main(argv)`.

Add private helpers:

- `_parse_design_clarify_args`
- `_validate_positive_int`
- `_fail_usage` (stderr message + exit 2 mirroring Bash `fail()`)
- `_build_driver_env` (allowlisted `os.environ` seed + `_load_source_env` overlay)
- `_plugin_root`
- `_cli_cmd`
- `_write_result_env`
- `_read_result_env`
- `_load_route_state_repo`
- `_stage_failed_clarify`
- `_append_clarify_failure`
- `_parse_publish_ok`
- `_emit_design_kvs`

Define:

- `CLARIFY_ENV_ALLOW = frozenset({"CLAUDE_PLUGIN_ROOT", "DESIGN_TMPDIR", "SESSION_ID", "ISSUE_NUMBER", "REPO"})`
- `ROUTE_STATE_ALLOW = frozenset({"REPO"})`
- `REQUEST_STATE_ALLOW = frozenset({"REQUEST_ID", "REQUEST_BODY_FILE", "PLAN_FILE", "RESPONSE_FILE", "ISSUE_NUMBER", "REPO"})`

Implementation details:

- Accept `--session-env-path`, `--claude-pid`, `--phase fetch|publish`, and `--issue N`.
- Env merge order: build from allowlisted `os.environ`, overlay `_load_source_env`, fall back `CLAUDE_PLUGIN_ROOT` to `Path(__file__).resolve().parents[1]`, resolve `DESIGN_TMPDIR` via `design_lifecycle._require_design_tmpdir(env)`.
- `_load_route_state_repo(env, design_tmpdir)`: skip when `REPO` set; absent sidecar continues with empty `REPO`; failure only when sidecar exists and allowlisted read fails.
- Phase-split route-state failure: fetch stages; publish does not.
- Shared startup order: env merge -> `DESIGN_TMPDIR` resolution -> route-state fallback -> repo validation -> pause check.
- Pause-save termination: call `design_pause.pause_save_main`, emit KVs, return immediately.

Fetch phase: call `clarify_state` and `clarify_comment_fetch` directly; map failures per token table; write result env files; emit KVs.

Publish phase: load request state; validate `REQUEST_ID` (exit 2, no result env on failure); redact with `redact.redact_secrets_only()`; call named-block write, log-publish, tracking-issue rename via subprocess; call `clarify_comment_post` and `clarify_label` directly; write result env; emit KVs.

Emit `SESSION_ID missing` warning on stdout when `SESSION_ID` is empty (Bash parity).

### UPDATED: python/cli.py

- Add `("design", "clarify"): ("clarify", "design_clarify_main")` to `_REGISTRY`.
- Add `("design", "clarify")` to `_DESIGN_LIFECYCLE_STDOUT_KEYS`.

### UPDATED: python/test_clarify.py

Add Python unit coverage for `design_clarify_main`.

Cover: env merge, absent-sidecar route-state no-op, phase-split route-state failure, fetch happy path, fetch failure tokens with `SUMMARY_OUTCOME=failed-clarify`, pause termination (no clarify work after pause, `clarify_state` not called), `_write_result_env` trust boundaries (symlink refuse, CR/LF reject, temp-then-rename), `_read_result_env` trust boundaries, publish happy path with `SESSION_ID missing` warning when `SESSION_ID` empty, invalid `REQUEST_ID` exit 2 with no result env, publish failure paths.

### UPDATED: python/test_design_cli_ports.py

Add `("design", "clarify"): ("clarify", "design_clarify_main")` to expected registry coverage.

### UPDATED: skills/design/scripts/design-clarify.sh

Replace with thin delegation wrapper using `_delegate_args` pattern:

```bash
_delegate_args=()
[ -z "${SESSION_ENV_PATH:-}" ] || _delegate_args+=(--session-env-path "$SESSION_ENV_PATH")
[ -z "${CLAUDE_PID:-}" ] || _delegate_args+=(--claude-pid "$CLAUDE_PID")
_delegate_args+=(--phase "$PHASE" --issue "$ISSUE")
exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design clarify "${_delegate_args[@]}"
```

Wrapper validates `--phase`, `--issue`, `--claude-pid` before delegation. Sources session env. Do not delete this file.

### UPDATED: skills/design/scripts/design-clarify.md

Update to document thin-wrapper nature, `_delegate_args` pattern, Python entrypoint, and fetch failure contract.

### UPDATED: skills/design/scripts/test-design-clarify.sh

Update harness to cover wrapper argv validation, `_delegate_args` reconstruction, and delegation. Remove old Bash internal fakes.

### UPDATED: skills/design/scripts/test-design-clarify.md

Update coverage text to reflect shell covers wrapper delegation; Python tests cover phase behavior.

## Edge cases

- `DESIGN_TMPDIR` missing, relative, nonexistent, or not a directory.
- `--issue`, `--claude-pid`, or `--phase` invalid (wrapper and Python, exit 2).
- `.design-step0-route-state.env` absent (benign, empty `REPO`) vs present and unreadable (phase-split failure).
- Invalid `REQUEST_ID`: exit 2, no publish result env.
- Result-env destination is symlink: write refused before stdout KVs.
- Result-env value contains CR or LF: write refused.
- `PLAN_FILE` or `RESPONSE_FILE` is empty, missing, or symlinked.
- Redaction raises or returns empty output.
- Empty `SESSION_ID`: skips log-publish and rename, emits warning.
- Pause after route-state resolution: terminates before clarify work.

## Failure modes

- Every live fetch failure emits `SUMMARY_OUTCOME=failed-clarify` (Final-summary routing depends on it).
- Absent route-state sidecar is benign; only present-sidecar read failure is `route-state-read-failed`.
- Fetch stages `_stage_failed_clarify`; publish does not.
- Invalid `REQUEST_ID` fails before result env write (exit 2).
- Log-publish failure is warning-only; still posts response and removes label.
- Rename failure is warning-only.

## Testing strategy

```bash
python3 -m pytest python/test_clarify.py python/test_design_cli_ports.py
make py-lint
make py-test
make lint
make test-design-structure
make test-design-clarify
```

## Notes

No `python/migrated-scripts.tsv` change needed: `design-clarify.sh` remains live as a thin wrapper.

No `SECURITY.md` update expected: parity port reuses existing session-env resolution and result-env trust boundaries.

## Acceptance

- [ ] `python/clarify.py`: `design_clarify_main` implements both phases with all parity invariants
- [ ] `python/cli.py`: `("design", "clarify")` in `_REGISTRY` and `_DESIGN_LIFECYCLE_STDOUT_KEYS`
- [ ] `python/test_clarify.py`: fetch/publish happy and failure paths covered including `SESSION_ID missing` warning and absent-sidecar route-state no-op
- [ ] `python/test_design_cli_ports.py`: registry entry covered
- [ ] `skills/design/scripts/design-clarify.sh`: thin `_delegate_args` wrapper; no business logic
- [ ] `skills/design/scripts/test-design-clarify.sh`: wrapper delegation and argv-validation tests pass
- [ ] `make py-lint` passes
- [ ] `make py-test` passes
- [ ] `make test-design-clarify` passes
- [ ] `make test-design-structure` passes

diff_lines: 1480

## Test plan
(no test plan section in plan-file)
