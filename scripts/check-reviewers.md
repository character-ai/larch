# scripts/check-reviewers.sh — contract

Checks external reviewer (Codex/Cursor, plus opt-in Gemini) binary availability and optional health probe.

## Tool registry

The script sources `scripts/external-tool-registry.sh` for the canonical external-tool iteration list, using a fail-closed source guard and sentinel check. The legacy probe set is preserved: Codex and Cursor by default, with Gemini included only when `--include-gemini` is passed. The Gemini probe runs with `--approval-mode plan` (least privilege) — the probe sends a fixed `"Respond with OK"` prompt and never invokes a tool, so it does not need the shell/file-read affordance the reviewer launcher (`scripts/launch-gemini-review.sh`) takes via `--approval-mode yolo`. Probe and reviewer share `scripts/lib-gemini-model-resolver.sh` for `$GEMINI_MODEL` resolution. The Codex probe argv mirrors the implementer launcher (`scripts/launch-codex-implement.sh`) by passing `--add-dir "$PROBE_DIR"`; this exercises the writable-roots flag production uses so a Codex build that rejects `--add-dir` fails the probe rather than failing later at `/implement` Step 2 spawn with worse diagnostics. The Codex probe also reads `agent-model-args.sh --tool codex` line-token stdout into `CODEX_MODEL_ARGS` (without `--with-effort`, matching `scripts/run-negotiation-round.sh`'s lightweight choice) so invalid `LARCH_CODEX_MODEL` / `CLAUDE_PLUGIN_OPTION_CODEX_MODEL` (blank, whitespace-only, or `[[:cntrl:]]`-bearing) is rejected at probe time with the same rules production launchers apply, instead of passing the probe and failing later in production with sentinel-timeout-then-failure diagnostics. The Cursor probe argv mirrors `scripts/launch-cursor-review.sh`'s production argv shape: it reads `agent-model-args.sh` line-token stdout into `CURSOR_MODEL_ARGS`, sources `scripts/lib-cursor-auth.sh`, and inserts `"${CURSOR_AUTH_ARGS[@]}"` (i.e., `--api-key "$CURSOR_API_KEY"` when the env var is set, nothing otherwise) between the model-args array and `--workspace`. `cursor_auth_preflight` is INTENTIONALLY NOT invoked from the probe — its job is to report binary health, not configuration validity; missing keychain entries should fail at production launch time with the actionable preflight error, not silently mark the binary unhealthy. If model-args validation fails, the probe writes a failure sentinel without invoking Cursor.

Per-tool getters/setters and `start_probe` arms remain explicit for Bash 3.2 portability, harness stability, and to avoid silent corruption under indirect expansion. Each switch helper has a defensive `*)` `internal error: unsupported reviewer tool: <id>` arm, so a registry update without matching switch updates fails loudly. Adding a new external tool requires both a registry update and a per-tool branch in every switch helper plus `start_probe`; `scripts/test-external-tool-registry.sh` walks every registry entry to catch missed branches.

Output keys (`CODEX_AVAILABLE`, `CURSOR_AVAILABLE`, `GEMINI_AVAILABLE`, `CODEX_HEALTHY`, etc.) remain stable for normal probe classification. A wait infrastructure failure adds `WAIT_INFRA_ERROR=<sanitized>` and emits every available tool's `*_HEALTHY=false` so downstream gates fail closed. Availability remains monotonic via `*_AVAILABLE=true`; `WAIT_INFRA_ERROR=` is the orthogonal diagnostic that tells consumers the failure came from probe infrastructure rather than a per-tool probe result. The value side of `WAIT_INFRA_ERROR=` may contain `=` characters; `session-setup.sh` parses by splitting on the first `=` only.

## Probe acceptance rule

With `--probe`, sends `"Respond with OK"` to each available tool with a 60-second timeout. The probe reply is normalized: all whitespace is stripped (`tr -d '[:space:]'`), then lowercased (`tr '[:upper:]' '[:lower:]'`). The result must equal exactly `"ok"` (case-insensitive exact match, NOT substring). This accepts `OK`, `ok`, `Ok`, `oK` (with any surrounding whitespace) and rejects empty output, error messages, verbose responses, and words containing "ok" as a substring (e.g., `token`, `broken`, `NotOK`). Gemini probes first parse the CLI JSON envelope with `jq -r '.response // empty'`; `.error` or missing `.response` fails the probe. The Gemini probe's `-m` argument resolves through `scripts/lib-gemini-model-resolver.sh`: `LARCH_GEMINI_MODEL` then `CLAUDE_PLUGIN_OPTION_GEMINI_MODEL`, defaulting to `gemini-2.5-pro` — so probe and reviewer always exercise the same model. Blank, whitespace-only, or `[[:cntrl:]]`-bearing model values write a failure sentinel (with diagnostic in `${output}.diag`) without invoking `gemini`, mirroring the rejection rules `scripts/agent-model-args.sh` enforces for Codex/Cursor.

Failed probes are retried up to 2 additional times (3 total attempts) with a 10-second sleep between attempts, applying the same acceptance rule each round. Each attempt only re-probes tools that are still unhealthy; healthy tools settle and stay healthy. Skipped tools (`--skip-codex-probe` / `--skip-cursor-probe` / `--skip-gemini-probe`) are settled as `*_HEALTHY=false` immediately and are never probed. The retry loop is data-driven over the selected tool list so adding a reviewer does not require pairwise `STILL_NEEDED` logic. Probe classification has three outcomes: healthy (`*_HEALTHY=true` after `evaluate_probe` accepts `OK`), unhealthy probe (`*_HEALTHY=false` plus `*_PROBE_ERROR=<reason>` from `evaluate_probe`), and wait infrastructure error (`WAIT_INFRA_ERROR=<sanitized>` plus every available tool's `*_HEALTHY=false`). The infrastructure-error path covers invalid wait config and non-zero `wait-for-reviewers.sh` exits such as host-side fatal errors; it does not infer per-tool failure, and it skips Gemini drift checks because discovery cannot run reliably when probe infrastructure failed.

When wait exits non-zero during a probe attempt, the script captures wait stdout and stderr separately, then reconstructs `wait-attempt<N>.log` as stdout, a literal `--- stderr ---` separator, then stderr. This compatibility log is not a temporally faithful interleave. Already-launched probe wrapper PIDs are tracked and reaped before the probe directory cleanup trap can remove files they might still write.

**Worst-case duration**: when both tools stay unresponsive across all 3 attempts, the upper bound is roughly 3 × 120s waits (per-attempt grace) + 2 × 10s inter-attempt sleeps ≈ 380s (~6m20s). This is up from the prior single-retry upper bound of ~240s. Callers with hard wallclock budgets (interactive timeouts, CI job limits) should account for this.

## Output keys

- `CODEX_AVAILABLE=true|false` — binary exists on PATH
- `CURSOR_AVAILABLE=true|false` — binary exists on PATH
- `GEMINI_AVAILABLE=true|false` — binary exists on PATH (only with `--include-gemini`)
- `CODEX_HEALTHY=true|false` — (only with `--probe`) exit 0 and normalized output == "ok"
- `CURSOR_HEALTHY=true|false` — (only with `--probe`) exit 0 and normalized output == "ok"
- `GEMINI_HEALTHY=true|false` — (only with `--probe --include-gemini`) exit 0 and JSON `.response` normalizes to "ok"
- `CODEX_PROBE_ERROR=<msg>` — (only on probe failure) diagnostic message
- `CURSOR_PROBE_ERROR=<msg>` — (only on probe failure) diagnostic message
- `GEMINI_PROBE_ERROR=<msg>` — (only on probe failure) diagnostic message
- `WAIT_INFRA_ERROR=<msg>` — (only when wait infrastructure failed) diagnostic message; paired with `*_HEALTHY=false` for each available tool. The value may contain `=` characters; consumers split on the first `=` only.
- `GEMINI_TOOL_DRIFT_WARNING=<msg>` — (only when `--probe --include-gemini` detects unknown Gemini tool names or an untrusted fixture)
- `GEMINI_TOOL_DRIFT_ARTIFACT=<path>` — (only when the Gemini drift artifact was written) path to `gemini-tool-drift.txt`

## Tool-name drift alarm

When Gemini is included, available, probed, and healthy, the normal probe-result branch runs a Gemini CLI tool-catalog drift alarm. The wait-infrastructure shortcut branch does not run the alarm.

The deny list is parsed from `scripts/gemini-reviewer-policy.toml` and treated as the source of truth. The parser expects the current single-line `toolName = [...]` TOML shape and fails closed if the parsed list is empty or misses any of today's five denied write tools: `write_file`, `replace`, `edit`, `edit_file`, and `delete_file`. Tests may point at an alternate policy with `LARCH_TEST_GEMINI_POLICY_PATH`.

The known-catalog fixture is `scripts/gemini-known-tools.txt`. Its checksum covers the body after excluding `#` header lines; a mismatch drops fixture entries from expected-tool classification, emits `GEMINI_TOOL_DRIFT_WARNING=fixture checksum mismatch - fixture untrusted`, and continues in deny-list-only mode. Tests may point at an alternate fixture with `LARCH_TEST_GEMINI_FIXTURE_PATH`.

Live discovery is best-effort: probe JSON metadata first, then `gemini /tools` with closed stdin and a 5-second timeout (`gtimeout`, `timeout`, or a process-group watchdog fallback), then fixture-only classification when live discovery is empty. `discover_gemini_tools_raw()` is the single live-discovery source and applies only printable-character sanitization plus the 64-byte cap. Strict-normalized streams are derived from that raw stream by lowercasing and filtering to snake-case identifiers for policy and set comparison. The artifact is written atomically to `<artifact-dir>/gemini-tool-drift.txt`; `--artifact-dir DIR` selects that directory, otherwise the ephemeral probe directory is used.

Named invariants: `[expected]` and `[observed]` artifact blocks consume the strict-normalized stream only; unknown-tool warnings and write-style classification consume raw discovered names; `discover_gemini_tools_raw()` is the single source and strict-normalized names are derived from it; human-readable warnings are authoritative for raw names while artifact blocks are intentionally strict-keyed.

Unknown live tool names produce `GEMINI_TOOL_DRIFT_WARNING=` and a matching `WARN: gemini-tool-drift:` stderr line. Tool names are sanitized with printable-character filtering and a 64-byte cap before emission. Write-style severity tokenizes raw names by splitting camelCase boundaries first, then replacing `_`, `-`, and `.` with spaces, then lowercasing and collapsing spaces. Matching uses the anchored regex `(^| )${kw}( |$)` against `write`, `edit`, `delete`, `replace`, `create`, `modify`, `save`, `put`, `post`, and `remove`; substring matching is forbidden. Deny-list coverage for a write-style raw name uses its strict-normalized policy key, so raw casing variants such as `WRITE_FILE` and `write_File` are covered by `write_file`, while non-strict names such as `write-file` remain uncovered. Any observed or fixture-known write-style tool missing from the deny list flips `GEMINI_HEALTHY=false` and appends a `GEMINI_PROBE_ERROR=gemini-tool-drift: ...` diagnostic.

This alarm validates gemini-cli CLI tool catalog drift under the health probe's `--approval-mode plan` argv. The reviewer launcher uses `--approval-mode yolo --admin-policy`, so probe-mode catalog drift is a proxy for reviewer-posture drift, not a strict guarantee.

## Flags

- `--probe` — run health probes (without this, only binary availability is checked)
- `--include-gemini` — include Gemini availability and probe output; callers omit it to preserve the legacy Codex+Cursor surface
- `--skip-codex-probe` — skip Codex probe (marks CODEX_HEALTHY=false)
- `--skip-cursor-probe` — skip Cursor probe (marks CURSOR_HEALTHY=false)
- `--skip-gemini-probe` — skip Gemini probe (marks GEMINI_HEALTHY=false)
- `--artifact-dir DIR` — write Gemini drift artifacts to `DIR/gemini-tool-drift.txt`; defaults to the ephemeral probe directory

## Test harness

`scripts/test-check-reviewers.sh` — regression tests for the probe acceptance logic using fixture replies and a stubbed Gemini integration probe. Covers positive cases (OK, ok, Ok, whitespace variants), negative cases (empty, token, broken, NotOK, error messages), Gemini `.response`, Gemini `.error`, Gemini model rejection, missing-`jq` fail-closed behavior, the wait preflight infrastructure-error contract (`WAIT_INFRA_ERROR`, fail-closed `*_HEALTHY=false`, value-side `=`, no retry loop, no sleeping probe wrapper launch), and the Gemini drift alarm's clean, benign, write-style, raw uppercase/mixed-case deny-list normalization, raw separator/camelCase write-style, anchored-token negative, discovery-unavailable, parser-failure, checksum-mismatch, fixture-undenied-write-style, and hung-discovery cases. Wired into `make test-harnesses`.

Compatibility audit: `git grep -nE 'WAIT_INFRA_ERROR|HEALTHY=(true|false|unknown)|FINAL_[A-Z]+_HEALTHY'` was reviewed for this change. Runtime consumers already gate launch eligibility on `*_AVAILABLE=true AND *_HEALTHY=true`. The `session-setup.sh` `.health` sidecar write block now uses fail-closed `${FINAL_*_HEALTHY:-false}` defaults (closes #1336) so an empty `FINAL_*_HEALTHY` (e.g., probe output omitted the key) emits `false`, not `true`, preserving the infra-error fail-closed contract end-to-end. See `scripts/session-setup.md` "Session-env contract" and `scripts/test-session-setup-health-defaults.sh` for the regression coverage.

## Edit-in-sync

| File | Relationship |
|------|-------------|
| `scripts/session-setup.sh` | Orchestrates probe invocation via `--check-reviewers`; opts into Gemini via `--check-gemini-reviewer`; parses health keys |
| `scripts/run-external-agent.sh` | Wrapper with timeout for probe subprocess |
| `scripts/wait-for-reviewers.sh` | Sentinel polling for probe completion |
| `skills/shared/external-reviewers.md` | Documents the two-key rule (`*_AVAILABLE` + `*_HEALTHY`) |
| `scripts/test-check-reviewers.sh` | Regression harness for acceptance logic |
| `scripts/lib-gemini-tool-drift.sh` | Gemini drift parser, discovery, classification, and artifact writer |
| `scripts/lib-gemini-model-resolver.sh` | Gemini model precedence and blank / `[[:cntrl:]]` rejection shared with launchers |
| `scripts/gemini-known-tools.txt` / `scripts/gemini-known-tools.md` | Gemini known-catalog fixture and checksum contract |
| `scripts/lib-cursor-auth.sh` | Cursor auth-argv builder + Darwin-gated keychain preflight; sourced for the Cursor probe argv (`cursor_auth_argv` only — preflight not invoked) |
