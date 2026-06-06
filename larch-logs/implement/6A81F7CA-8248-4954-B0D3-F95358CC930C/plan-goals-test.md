## Goal
Implement issue #3476: [IMPLEMENTING] Codex auth test harness gaps (strip failure, probe coverage, review-and-fix dispatch)\n\n## Out-of-Scope Observation.

## Implementation Plan
## Plan

## Context

PR #3477 (Fixes #3411) added shared Codex auth helpers and wired them into probe, review-fix, and implement launch paths. Issue #3476 tracks remaining harness gaps. This plan adds only missing assertions; already-covered strip failure, review-and-fix telemetry leak checks, implementer login fallback, and 4h KV envelope remain out of scope.

## Files to modify/create

### UPDATED: `scripts/test-lib-external-launcher-common.sh`

1. Fix defective post-table assertion:
   - After `external_prepare_codex_auth` on the copied login config fixture, run post-table retention assertions on `login-home/config.toml` (not `strip-edge-config.toml`):
     - Preflight `[[ -f login-home/config.toml ]]` before any `grep -Fxc` count.
     - Assert zero exact retained `model_provider = "openai-larch-env"` using `grep -Fxc ... || true`; the copied login fixture’s surviving selector-like text is multiline/prefixed, not an exact standalone selector.
     - Assert zero retained `env_key = "OPENAI_API_KEY"`.
     - Assert the nested `[model_providers.other]` selector is absent.
   - Keep `strip-edge-config.toml` for direct `external_strip_codex_larch_env_provider` edge cases only; do not duplicate post-table provider/env_key count assertions there.

2. Add multiline-state corruption fixtures:
   - Keep these in separate temp configs from the exact-count post-table fixture.
   - Stripped selector with trailing `"""` comment must not toggle multiline state.
   - `'''` multiline body containing selector/table header remains verbatim, with targeted assertions against the retained multiline-body lines.
   - Same-line closing `"""` before a real larch table must exit multiline state cleanly so the table is stripped.

### UPDATED: `scripts/test-check-reviewers.sh`

1. Add `assert_no_probe_homes <label> <tmpdir>` using `find "$tmpdir" -maxdepth 1 -name 'larch-codex-probe-home.*'`.
2. Assert cleanup after t6 success, t7 non-auth failure, t9 auth-retry exhausted, t7a auth-prep helper failure, and existing timeout case `t-probe-to`.
3. Extend a live env-key probe case, explicitly `t10-env-key-false` or equivalent false/missing env-key-stamp case that sets `OPENAI_API_KEY=<REDACTED-TOKEN>` and `LARCH_TEST_CODEX_ARGV_LOG`, to assert trusted-project `-c` entries.
   - Assert adjacent argv pairing: a `-c` argv entry immediately followed by the exact trusted-project config string containing `trust_level="trusted"` and `projects.`.
   - Keep t10 stamp-hit coverage login/stamp-focused; do not attach argv or sentinel assertions to a case that skips Codex.
   - In the same argv capture, assert auth override adjacency too: each env-key override config string (`model_provider="openai-larch-env"` and `model_providers.openai-larch-env.env_key="OPENAI_API_KEY"`, matching production quoting) must appear as the argv entry immediately after its own `-c`.
   - Do not accept bare string-presence greps for these auth overrides; the assertion must fail if the required preceding `-c` is missing or separated.
4. After that same live env-key probe case, recursively grep the case’s private `TMPDIR` for absence of `<REDACTED-TOKEN>`.
5. Add legacy env-key strip case using `run_cr_with_env` or equivalent direct wrapper with `OPENAI_API_KEY` set and `HOME` pointed at the fixture:
   - Capture temp config without production changes: in that case’s test-local `codex` PATH stub, copy `$CODEX_HOME/config.toml` to `$LARCH_TEST_CODEX_CONFIG_CAPTURE` when both are set.
   - Assert larch selector/env_key/literal credential stripped.
   - Assert `[profiles.keep]` retained.
   - Assert original fixture config unchanged.
6. Add stamp isolation checks:
   - Env-key probe writes only env-key stamp.
   - Login probe writes only login stamp.
   - Fresh env-key stamp with no `OPENAI_API_KEY` must not satisfy login-mode probe and must exercise the login path:
     - Run in a fresh per-case TMPDIR via `run_cr` or an explicit subshell with `unset OPENAI_API_KEY`.
     - Fixture contract: no fresh `codex-login` stamp (absent, `false`, or expired) so the probe cannot short-circuit before exercising login-path argv/symlink wiring.
     - Keep the env-key stamp as decoy; assert live-probe argv lacks env-key overrides and/or shows login auth material.

### UPDATED: `skills/review-and-fix/scripts/test-review-and-fix.sh`

All cases go inside the existing `dispatch` section.

1. Extend the inline heredoc stub generated near the top of `test-review-and-fix.sh` (not a standalone file) with `TEST_AGENT_CODEX_AUTH_LINK_FILE`: when set and `$CODEX_HOME/auth.json` is a symlink, write `readlink` output to the capture file.
2. Add login-mode auth-prep failure case:
   - Force prep failure with a test-only conditional/delegating `mv` stub on `PATH` (mirroring `skills/implement/scripts/test-codex-implementer.sh`) or an equivalent guaranteed temp-`CODEX_HOME` prep failure; do not rely on a read-only source config alone.
   - If using the `mv` stub, fail only the temp `larch-codex-review-fix-home.*` Codex config rewrite/rename and delegate every other `mv` invocation to `/bin/mv` so Cursor fallback and later harness writes are not polluted.
   - If a read-only fixture is still used as supporting setup, restore `chmod u+w` immediately after the function returns, before assertions.
   - Invoke `run_review_and_fix` from a subshell/function-safe environment that exports a dedicated harness temp dir: `( unset OPENAI_API_KEY; export TMPDIR="$case_tmp"; mkdir -p "$TMPDIR"; HOME="$fixture_home" TEST_AGENT_BEHAVIOR=cursor-success ... run_review_and_fix ... )` with `case_tmp` allocated per case.
   - Assert wrapper log contains auth setup failure, codex argv capture is absent, fallback succeeds with `CODER_TOOL=cursor`.
   - Snapshot the case-private exported `TMPDIR` before/after with `find "$TMPDIR" -maxdepth 1 -name 'larch-codex-review-fix-home.*'` and fail only on new survivors, because this auth-prep failure path skips Codex dispatch and cannot use a captured `CODEX_HOME` file.
3. Add login fallback with fixture:
   - Run in a subshell that unsets `OPENAI_API_KEY`, then set `HOME="$fixture_home"` containing `.codex/auth.json`.
   - Set `TEST_AGENT_ARGV_FILE` and `TEST_AGENT_CODEX_AUTH_LINK_FILE`.
   - Assert auth symlink points to fixture auth, env-key argv overrides are absent, `CODER_TOOL=codex`.
4. Add env-key Codex dispatch failure breadcrumb:
   - Set `OPENAI_API_KEY=<REDACTED-TOKEN>`, `TEST_AGENT_BEHAVIOR=cursor-success`, and `TEST_AGENT_ARGV_FILE=<capture>`.
   - Also set `TEST_AGENT_CODEX_HOME_FILE=<capture-home>` in this same case so cleanup is pinned to the env-key dispatch-failure Cursor fallback path.
   - Assert wrapper log and sidecar contain `codex-env-key-failure: Codex dispatch failed on the OPENAI_API_KEY auth path`.
   - Assert `CODER_TOOL=cursor`.
   - Assert sentinel absent from wrapper log, sidecar, and argv capture.
   - Read the captured `larch-codex-review-fix-home.*` path and assert it no longer exists after `run_review_and_fix` returns.
5. Keep env-key auth-prep-failure breadcrumb untested because it is unreachable under current production semantics (`external_prepare_codex_auth` returns 0 on the OPENAI_API_KEY branch; strip/mv errors are best-effort) unless `lib-external-launcher-common.sh` changes — mirror `test-codex-implementer.sh` item 3. Retain item 4 env-key dispatch-failure breadcrumb and cleanup coverage instead.

### UPDATED: `skills/implement/scripts/test-codex-implementer.sh`

1. Add guarded `/tmp` snapshot helper for temp homes:
   - Use `{ ls -d /tmp/larch-codex-home-* 2>/dev/null || true; } | LC_ALL=C sort`.
   - Compare before/after and fail only on paths absent from the before snapshot.
2. Apply cleanup assertion to:
   - Existing happy-path launch.
   - Existing 4h auth-prep-failure launch.
3. Keep env-key auth-prep-failure breadcrumb untested because it is unreachable by fixture design.

## Approach

- Tests and fixtures only; no production-script changes.
- Use existing harness idioms: `pass`/`fail`, `run_cr`, `run_cr_with_env`, per-test `TMPDIR`, `make_work_repo`, `run_review_and_fix`, and `STUB_*`/`TEST_AGENT_*` captures.
- Keep all new Bash compatible with Bash 3.2: no `mapfile`, associative arrays, or process features beyond existing harness style.
- For read-only fixture failure paths, restore permissions immediately after the child/function call returns, before any assertions.
- For shell functions, do not invoke with `env -u`; use a subshell with `unset OPENAI_API_KEY`, especially for login-mode dispatch assertions.
- When shadowing common tools in review-and-fix tests, use narrowly targeted stubs that trigger only the intended Codex auth-prep operation and delegate all unrelated calls to the system tool.

## Edge cases

- Guard `grep -c`/`grep -Fxc` with `|| true` before comparing counts.
- Ensure fixture `HOME` is exported/set on every review-and-fix dispatch case that relies on `.codex`.
- Avoid vacuous sentinel assertions by always creating argv capture when checking argv.
- Timeout cleanup is pinned alongside success/failure/retry/helper-failure probe paths.
- Trusted-project argv checks must prove `-c` adjacency, not merely that the config string appears somewhere in argv.
- Env-key auth override argv checks must also prove `-c` adjacency for both `model_provider` and `env_key` overrides, not merely string presence.
- Temp config capture for check-reviewers stays inside the test-local Codex stub; no shipped probe/config-capture hook is added.
- `/tmp` implementer cleanup assertion tolerates pre-existing dirs and only fails on new survivors.
- Review-and-fix login auth-prep cleanup requires a case-private exported `TMPDIR` (`export TMPDIR="$case_tmp"; mkdir -p "$TMPDIR"`) before `run_review_and_fix` so survivor scans are not vacuous against unrelated global `/tmp` state.
- Review-and-fix env-key dispatch-failure cleanup is asserted in the same fallback case that records the env-key breadcrumb, not in an unrelated Codex-success case.
- Stamp-isolation login-path subcase unsets `OPENAI_API_KEY` and ensures no fresh `codex-login` stamp so login-path argv/symlink wiring is actually exercised.
- Post-table provider/env_key exact-count assertions target `login-home/config.toml` after `external_prepare_codex_auth` and expect zero exact standalone larch selector/env_key lines; `strip-edge-config.toml` remains for direct strip edge cases only.

## Failure modes

1. **False-green assertions.** Mitigate by mutation sanity checks: flip one new assertion per harness and confirm failure.
2. **Concurrent `/tmp` noise.** Snapshot diff only reports new survivors; CI single-runner behavior keeps this stable.
3. **Read-only cleanup litter.** Restore write permissions immediately after the run returns.
4. **Fixture HOME leaks.** Explicitly bind `HOME="$fixture_home"` for each fixture-dependent dispatch run.

## Testing strategy

- Run direct harnesses:
  - `make test-lib-external-launcher-common test-check-reviewers test-codex-implementer`
  - `bash skills/review-and-fix/scripts/test-review-and-fix.sh --section dispatch`
- Run mutation sanity checks for one new assertion per harness.
- Run `bash scripts/relevant-checks.sh` and `make lint-bash32`.

## Acceptance

- `scripts/test-lib-external-launcher-common.sh`: post-table retention assertions run against `login-home/config.toml` with `grep -Fxc ... || true` counts (zero standalone larch selector/env_key lines; nested `[model_providers.other]` selector absent); the three multiline-state fixtures (trailing-`"""`-comment, `'''` body retention, clean multiline exit before a stripped larch table) are present and pass.
- `scripts/test-check-reviewers.sh`: `assert_no_probe_homes` fires after success, non-auth failure, auth-exhaust, auth-prep failure, and timeout cases; trusted-project and env-key override argv assertions prove `-c` adjacency; the sentinel sweep over the case-private `TMPDIR` finds no `<REDACTED-TOKEN>`; the legacy strip case proves temp-copy stripping with fixture `HOME` unchanged; stamp write/read isolation cases pass in both auth modes.
- `skills/review-and-fix/scripts/test-review-and-fix.sh` (`--section dispatch`): login-mode auth-prep failure case asserts the `codex-auth-setup:` breadcrumb, no codex invocation, cursor fallback, and no new `larch-codex-review-fix-home.*` survivors; login-fallback case asserts the fixture `auth.json` symlink and no env-key argv; env-key dispatch-failure case asserts the `codex-env-key-failure:` breadcrumb in wrapper log and sidecar, cursor fallback, sentinel absence, and temp-home removal.
- `skills/implement/scripts/test-codex-implementer.sh`: `/tmp/larch-codex-home-*` snapshot-diff cleanup assertions pass on the happy-path and 4h auth-prep-failure launches.
- All four harnesses pass: `make test-lib-external-launcher-common test-check-reviewers test-codex-implementer` and `bash skills/review-and-fix/scripts/test-review-and-fix.sh --section dispatch`.
- `bash scripts/relevant-checks.sh` and `make lint-bash32` pass on the edited files.
- No production scripts, no new files, and no Makefile/CI wiring changes are introduced.

diff_added: 456
diff_deleted: 22
diff_lines: 478

## Test plan
(no test plan section in plan-file)
