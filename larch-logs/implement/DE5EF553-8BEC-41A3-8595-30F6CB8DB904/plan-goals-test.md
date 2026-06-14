## Goal
Implement issue #4167: [IMPLEMENTING] External reviewer launcher.

## Implementation Plan
## Plan

## Approach

- Add `python/cli.py agent launch-review` as the canonical Codex/Cursor review launcher.
- Port behavior, not shell structure.
- Keep all launcher contracts stable:
  - accepted flags and exit codes
  - `.meta`, `.prompt`, `.done`, `.inner.done`, `.diag`, `.sidecar`, `.dirty-tree`, `.events.jsonl`, `.token-record`, and `.cap-hit` sidecars
  - `OUTER_LAUNCHER*` retry metadata
  - Codex compact prompt sentinel behavior
  - Cursor original-prompt sidecar behavior
  - Cursor baseline dirty-tree streams used by review recovery
  - gated `LARCH_TEST_TRAP_AFTER_INNER_DONE_FILE` hook
  - `LARCH_TOKEN_BUDGET_CAP_REVIEW` fallback when `--token-budget-cap` is absent
  - token session binding from `IMPLEMENT_TMPDIR/session-id`, then `DESIGN_TMPDIR/session-id`
  - launch-failure logging to the resolved execution-issues log for implement or design contexts
  - vendor-failure diagnostics staging when `IMPLEMENT_TMPDIR` is set
- Route vendor execution through the existing in-process `run_external_agent` wrapper per attempt.
- Add explicit review-specific retry loops around that wrapper.
- Do not rely on auth-only retry helpers for full review retry behavior.
- Wrap the external serial lock around every vendor spawn:
  - initial attempts
  - auth retries
  - transient retries
  - Cursor empty-result retries
- Preserve wrapper-owned contracts:
  - `.meta` TOOL/TIMEOUT fields
  - `.inner.done`
  - timeout handling
  - stall handling
  - stdout/stderr capture behavior
- Keep review dirty-tree semantics distinct:
  - Codex read-only review writes the static clean sidecar.
  - Codex auth setup failure preserves bash parity: static clean read-only sidecar.
  - Codex model-args preflight failure writes an unknown dirty-tree sidecar.
  - Cursor auth/model preflight failures write unknown dirty-tree sidecars.
  - Cursor captures a pre-launch NUL untracked baseline with Python git snapshot helpers.
  - Cursor writes baseline-mode dirty-tree sidecars with Python dirty-tree baseline helpers.
  - Do not use `dirty-tree checkpoint` for review baseline handling.
- Retarget live callers to `python3 "$SCRIPT_DIR/../python/cli.py" agent launch-review`.
- Retarget collector retry metadata so canonical retries invoke the Python verb directly.
- Accept only `OUTER_LAUNCHER=agent launch-review` for review retries after cutover.
- Fail closed on retired review shell launcher metadata.
- Never execute retired review launcher metadata directly.
- Delete the retired shell launcher, its contract doc, and shell harnesses after pytest parity lands.
- Update active docs, rules, harnesses, and security references.
- Avoid exact retired-path literals outside `python/migrated-scripts.tsv`.
- Build retired-path fixture strings programmatically in tests when validating fail-closed behavior.
- Run retired-script lint so stale references are removed or explicitly represented only through the manifest.

## Files to modify/create

### UPDATED: python/agents.py

Add `launch_review_main(argv=None)` and private helpers near existing launcher helpers.

Implement parser support:

- Required:
  - `--tool codex|cursor`
  - `--output`
  - `--timeout`
  - exactly one of `--prompt`, `--prompt-file`, `--agent-file`
- Shared optional flags:
  - `--mode`
  - `--description-text`
  - `--scope-files`
  - `--competition-notice`
  - `--competition-notice-file`
  - `--diff-file`
  - `--commit-count`
  - `--plan-file`
  - `--feature-file`
  - `--timing-task-kind`
  - `--token-budget-cap`
  - `--risk`
  - `--stderr-sink`
- Codex-only optional flag:
  - `--codex-add-dir`

Validate before side effects:

- `--output` and `--stderr-sink` with the safe meta-path predicate used by `run_external_agent_main`.
- `--timeout` as a positive integer.
- `--timing-task-kind` as non-empty and not flag-shaped.
- `--token-budget-cap` as a positive integer.
- `--tool` against `codex|cursor`.

Add prompt helpers:

- `_review_render_specialist_prompt(args)`.
- `_review_read_prompt_file(path)`.
- `_review_read_codex_prompt_sentinel(path)`.
- `_review_write_codex_prompt_sidecar(output, prompt, args)`.
- `_review_write_cursor_prompt_sidecar(output, original_prompt)`.

Add shared launch helpers:

- `_review_apply_session_token_env()`.
- `_review_apply_claude_source_env()`.
- `_review_effective_token_cap(args)`.
- `_review_check_budget_or_write_cap_hit(output, cap, timing_kind)`.
- `_review_record_timing(vendor, task_kind, start_s, output, exit_code)`.
- `_review_append_outer_meta(meta, *, prompt_sidecar, risk, stderr_sink)`.
- `_review_write_clean_readonly_dirty_tree(output)`.
- `_review_write_unknown_dirty_tree(output, reason)`.
- `_review_capture_cursor_dirty_baseline(output)`.
- `_review_write_cursor_dirty_tree_from_baseline(output, baseline)`.
- `_review_append_launch_failure(...)`.
- `_review_run_test_trap_after_inner_done_if_enabled()`.

Pin token cap behavior:

- If `--token-budget-cap` is present, use the parsed positive integer.
- If `--token-budget-cap` is absent, read `LARCH_TOKEN_BUDGET_CAP_REVIEW`.
- Use `LARCH_TOKEN_BUDGET_CAP_REVIEW` only when it is a positive integer.
- Treat absent or non-positive env values as no cap.
- Preserve cap-hit behavior: write `.cap-hit`, write `.done`, optionally write `step-budget-cap-hit.env`, exit process 0, and skip vendor launch.

Pin session-token behavior:

- `_review_apply_session_token_env` reads `IMPLEMENT_TMPDIR/session-id` first.
- If no implement session id exists, it reads `DESIGN_TMPDIR/session-id`.
- When a session id is found, export or set `LARCH_TOKEN_SESSION_ID` for vendor launch and timing/usage helpers.
- Preserve existing caller-provided `LARCH_TOKEN_SESSION_ID` only when no session-id file is available.

Pin launch-failure logging:

- Implement `_review_append_launch_failure` through `agents._resolve_execution_issues_log()` or the shared Python equivalent.
- Log to `IMPLEMENT_TMPDIR/execution-issues.md` when implement context is active.
- Log to `DESIGN_TMPDIR/execution-issues.md` when implement context is absent and design context is active.
- Include verdict and retry metadata in run-log append-failure calls.
- Call `agents._append_vendor_failure_diagnostics` or the shared Python equivalent when `IMPLEMENT_TMPDIR` is set.
- Preserve `review Step 2` batch naming for vendor failure diagnostics.

Pin Cursor dirty-tree helpers:

- Implement `_review_capture_cursor_dirty_baseline` through in-process Python git snapshot functionality with NUL output.
- If an internal CLI boundary is needed, use `python/cli.py git snapshot-untracked --output <baseline> --nul`.
- Implement `_review_write_cursor_dirty_tree_from_baseline` through the Python dirty-tree baseline API.
- If an internal CLI boundary is needed, use `python/cli.py dirty-tree baseline --baseline <baseline> --sidecar <output>.dirty-tree`.
- Preserve `UNTRACKED_BASELINE`, `TRACKED_PATHS_FILE`, and `NEW_UNTRACKED_PATHS_FILE`.
- Do not reimplement ad hoc git diff parsing in the launcher.
- Do not use checkpoint behavior for Cursor review dirty-tree detection.

Implement review-specific retry loops:

- Call the in-process `run_external_agent` wrapper for each vendor attempt.
- Acquire and release the external serial lock around every `run_external_agent` call.
- Use `capture_stdout_only` for Cursor.
- Preserve auth retries separately from transient retries.
- Reacquire the serial lock for every auth retry attempt.
- Reacquire the serial lock for every transient retry attempt.
- Reacquire the serial lock for every Cursor empty-result retry attempt.
- Preserve transient retry bounds.
- Preserve sidecar history resets between retry attempts.
- Preserve quota skip behavior for Codex events.
- Preserve Cursor exit-0 empty `.result` retry.
- Preserve Cursor jittered backoff.
- Preserve `LARCH_TRANSIENT_RETRY_DELAY`.
- Preserve final failure classification and diagnostics.

Implement exit-code parity:

- Token cap hit writes `.cap-hit`, `.done`, and exits process 0.
- Env-only token cap hit from `LARCH_TOKEN_BUDGET_CAP_REVIEW` behaves the same as a flag cap hit.
- Codex auth setup failure writes the preflight bundle, exits process 0, preserves the existing `.done` status payload, and writes the static clean read-only dirty-tree sidecar.
- Codex model-args failure writes the preflight bundle, writes unknown `.dirty-tree`, and exits non-zero.
- Cursor auth preflight failure writes the same contract, writes unknown `.dirty-tree`, and exits non-zero.
- Cursor model-args failure writes the same contract, writes unknown `.dirty-tree`, and exits non-zero.
- Final vendor failures keep existing non-zero exit behavior.
- Add tests for the matrix.

Codex path:

- Build strict read-only instructions into per-invocation `CODEX_HOME/config.toml`.
- Keep `CODEX_HOME` outside the output tree.
- Reject TOML `'''` in injected instructions.
- Preserve `codex exec --sandbox read-only -C "$PWD" --add-dir <sandbox_dir> ... --output-last-message <output> --json -- <prompt>`.
- Validate `--codex-add-dir`:
  - existing directory
  - no control chars
  - no `..`
  - not a symlink
  - canonical path under the canonical output directory
- Resolve model args with `resolve_model_args("codex", with_effort=True)`.
- On auth setup preflight failure, write the same bundle shape and static clean read-only `.dirty-tree`.
- On model-arg preflight failure, write the same bundle shape and unknown `.dirty-tree`.
- Write `output.prompt` before launch.
- Capture events to `output.events.jsonl`.
- Capture stderr to `output.sidecar`, or `/dev/null` if needed.
- Do not leak API keys into argv, metadata, prompt sidecars, or diagnostics.
- Mirror quota signals before transient classification.
- On final non-zero, compose diagnostics, classify verdict, append run-log failure, and stage vendor diagnostics.
- On success, append `codex-status: ok...` when applicable.
- Record Codex usage.
- Pin terminal order:
  1. Finish retry loop.
  2. Append outer metadata.
  3. Record usage and timing.
  4. Run Codex finally/exit-dispatch behavior.
  5. Write static read-only dirty-tree sidecar.
  6. Promote `.inner.done` to `.done`.

Cursor path:

- Resolve model args with `resolve_model_args("cursor", with_effort=True)`.
- Preserve Cursor strict preamble and prompt wrapping.
- Launch `cursor agent -p --trust --mode ask --output-format json <model args> --workspace "$PWD" "$WRAPPED_PROMPT"`.
- Keep no `--api-key` argv element.
- Run Cursor auth preflight before launch.
- Run Python equivalents of keychain preread and auth export before launch.
- Preserve `CURSOR_API_KEY` inheritance.
- On auth preflight failure, synthesize the same output, `.diag`, `.meta`, `.dirty-tree`, and `.done` bundle with unknown dirty-tree status.
- Isolate `CURSOR_CONFIG_DIR` with a distinct temporary directory per launch.
- Seed `CURSOR_CONFIG_DIR` from `~/.cursor/cli-config.json`.
- Capture the pre-launch NUL untracked baseline before vendor launch.
- Preserve random launch jitter from `LARCH_CURSOR_LAUNCH_JITTER_MS`.
- Preserve bounded transient retry and exit-0 empty `.result` retry.
- Preserve final Cursor JSON post-processing:
  - copy raw JSON to `output.json`
  - extract `.result` atomically with Python JSON
  - keep original bytes on malformed JSON
  - normalize same-line narration plus `{"no_issues_found": true}`
  - call `eval validate-research-output` with existing thresholds
  - write `CURSOR_DEGRADED_RESPONSE` only when the existing gate matches
  - write `CURSOR_EMPTY_RESPONSE` and detailed `.diag` for empty `.result`
  - record Cursor usage
- On final non-zero, compose diagnostics, append run-log failure, and stage vendor diagnostics.
- Pin terminal order:
  1. Finish retry loop.
  2. Append outer metadata.
  3. Run gated test trap after `.inner.done` exists.
  4. Run JSON post-processing.
  5. Write Cursor baseline dirty-tree sidecar.
  6. Promote `.inner.done` to `.done`.

### UPDATED: python/cli.py

Register:

- `("agent", "launch-review"): ("agents", "launch_review_main")`

Add it to `_MACHINE_STDOUT_KEYS` only if stdout is consumed as machine-readable `KEY=VALUE` lines.

### NEW: python/test_launch_review.py

Add focused pytest parity coverage.

Cover parser and validation:

- missing `--tool`
- invalid tool
- missing `--output`
- missing `--timeout`
- zero, zero-padded zero, and non-numeric timeout
- mutually exclusive prompt sources
- missing prompt source
- invalid `--timing-task-kind`
- invalid `--token-budget-cap`
- unsafe `--output`
- unsafe `--stderr-sink`

Cover prompt sidecars:

- Codex `--agent-file` writes exact compact sentinel keys.
- Codex sentinel replay reconstructs and hash-verifies.
- Codex sentinel hash mismatch fails closed.
- Codex `--description-text` writes full prompt.
- Cursor writes original prompt sidecar.
- Cursor retry does not prepend strict preamble twice.

Cover token and session behavior:

- `--token-budget-cap` cap hit writes `STATUS=cap_hit`, `.cap-hit`, `.done`, optional `step-budget-cap-hit.env`, exits 0, and skips vendor launch.
- Env-only `LARCH_TOKEN_BUDGET_CAP_REVIEW` cap hit behaves the same when `--token-budget-cap` is absent.
- Non-positive or non-integer `LARCH_TOKEN_BUDGET_CAP_REVIEW` is not used as a cap.
- `IMPLEMENT_TMPDIR/session-id` sets `LARCH_TOKEN_SESSION_ID`.
- `DESIGN_TMPDIR/session-id` sets `LARCH_TOKEN_SESSION_ID` when implement session id is absent.
- Implement session id wins when both implement and design session-id files exist.

Cover preflight bundles and process exit codes:

- Codex auth setup failure writes empty output, `.diag`, `.meta`, `.done`, static clean read-only `.dirty-tree`, and exits 0.
- Codex model-args failure writes the same contract, writes unknown `.dirty-tree`, and exits non-zero.
- Cursor auth preflight failure writes the same contract, writes unknown `.dirty-tree`, and exits non-zero.
- Cursor model-args failure writes the same contract, writes unknown `.dirty-tree`, and exits non-zero.

Cover wrapper, locking, and retry behavior:

- Vendor attempts route through in-process `run_external_agent`.
- `.meta` includes TOOL/TIMEOUT.
- `.inner.done` is created by the wrapper.
- Cursor uses `capture_stdout_only`.
- Auth retry reacquires the serial lock per attempt.
- Transient retry reacquires the serial lock per attempt.
- Cursor empty-result retry reacquires the serial lock per attempt.
- Every external vendor spawn is inside the serial lock.
- Transient 0-output failures retry within the configured bound.
- Retry attempts reset sidecar history.
- Quota in Codex events skips transient retry.
- Cursor empty `.result` exit-0 retries when enabled.
- Cursor empty `.result` does not retry when disabled.

Cover launch contracts with stub binaries:

- Codex argv includes `exec --sandbox read-only`, `--add-dir`, `--output-last-message`, and `--json`.
- Codex argv and artifacts do not leak secrets.
- Cursor argv includes `agent -p --trust --mode ask --output-format json --workspace`.
- Cursor argv has no `--api-key`.
- `CURSOR_API_KEY` is inherited when set.
- Cursor keychain preread and auth export helpers run before launch.
- `OUTER_LAUNCHER=agent launch-review` metadata is appended.
- `STDERR_SINK` is preserved when passed.
- Success status lines are appended when sidecars are real files.

Cover launch-failure diagnostics:

- Final failure composes `output.failure-diag`.
- Final failure calls run-log append-failure with `review Step 2`.
- Final failure includes verdict and retry metadata in the append-failure path.
- `DESIGN_TMPDIR` without `IMPLEMENT_TMPDIR` writes launch failures to the design execution-issues log.
- `IMPLEMENT_TMPDIR` writes launch failures to the implement execution-issues log.
- `IMPLEMENT_TMPDIR` final vendor failures stage vendor diagnostics through the Python vendor diagnostics helper.

Cover terminal ordering:

- Codex appends outer metadata and records usage before dirty-tree sidecar and `.done` promotion.
- Codex writes the static read-only dirty-tree sidecar even on launcher exit paths that match bash parity.
- Codex model-args preflight writes unknown dirty-tree status.
- Cursor appends outer metadata before test trap.
- Cursor runs test trap before JSON post-processing.
- Cursor writes dirty-tree sidecar after JSON post-processing.
- Cursor promotes `.done` last.

Cover post-processing:

- Codex usage events create or emit a token sidecar.
- Cursor JSON `.result` extraction is atomic.
- Cursor same-line no-issues sentinel normalizes to bare JSON.
- Cursor degraded-response gate matches existing behavior.
- Cursor empty result writes `CURSOR_EMPTY_RESPONSE` and `.diag`.
- Final failure composes `output.failure-diag`.
- Final failure calls run-log failure append with `review Step 2`.

Cover dirty-tree:

- Codex read-only path writes clean static dirty-tree sidecar.
- Codex auth setup failure writes clean static dirty-tree sidecar.
- Codex model-args failure writes unknown dirty-tree sidecar.
- Cursor captures pre-launch NUL untracked baseline before vendor launch.
- Cursor baseline capture uses Python git snapshot semantics, not checkpoint semantics.
- Cursor writes baseline-mode dirty-tree sidecar before `.done`.
- Cursor baseline emission uses Python dirty-tree baseline semantics.
- Cursor dirty sidecar includes `UNTRACKED_BASELINE`, `TRACKED_PATHS_FILE`, and `NEW_UNTRACKED_PATHS_FILE`.
- Pre-existing worktree dirt does not become reviewer dirt.
- Preflight Cursor paths write unknown sidecars.
- Review launch does not use checkpoint behavior for Cursor baseline detection.

Cover security and isolation:

- `CODEX_HOME` is per invocation and outside the output tree.
- Secrets do not appear in argv or artifacts.
- `--codex-add-dir` accepts an in-output canonical directory.
- `--codex-add-dir` rejects non-directory, symlink, control-character, `..`, and outside-output paths.
- Parallel Cursor launches receive distinct `CURSOR_CONFIG_DIR` values.

### UPDATED: python/test_agents.py

Keep shared helper tests here when they are not specific to review launch.

Move launcher-specific tests to `python/test_launch_review.py` only when needed.

### UPDATED: scripts/dispatch-with-waterfall.sh

Replace non-Claude review launch branches with:

- `python3 "$SCRIPT_DIR/../python/cli.py" agent launch-review --tool "$tool" ...`

Keep stdout/stderr redirection and `.done` fallback behavior unchanged.

### UPDATED: scripts/collect-agent-results.sh

Retarget outer retry metadata.

- Accept `OUTER_LAUNCHER=agent launch-review` as the only canonical review launcher.
- Add an explicit `agent launch-review` case before path validation.
- Treat this token as non-filesystem metadata.
- Skip canonicalization and executable probes for the canonical token.
- Fail closed on retired review launcher path metadata.
- Do not add a legacy compatibility replay arm.
- Do not require the retired shell file to exist.
- Never execute `META_OUTER_LAUNCHER` directly for review retry.
- Keep `agent launch-codex-exec` unchanged.
- Keep fail-closed validation:
  - all three review outer fields must be present
  - prompt sidecar pinned to `${orig_output}.prompt`
  - workdir must exist
  - workdir must not contain `..`
  - risk coerces to `high|low`
  - stderr sink validation remains
  - retired review launcher paths are rejected after cutover
- Retry review launches with `python3 "$SCRIPT_DIR/../python/cli.py" agent launch-review`.
- Preserve test hook scrubbing with `env -u LARCH_ALLOW_TEST_HOOKS ...`.
- Update assertion text to `agent launch-review`.

### UPDATED: scripts/test-collect-agent-retry.sh

Retarget retry fixtures and expectations.

- Use `OUTER_LAUNCHER=agent launch-review` for valid canonical review metadata.
- Add fail-closed fixtures for retired review launcher metadata.
- Construct retired launcher path strings from components.
- Expect canonical metadata to replay through `python3 ... python/cli.py agent launch-review`.
- Assert retired launcher metadata is rejected and never executed.
- Assert retired metadata validation fails closed for outside-repo paths, non-canonical paths, and paths containing `..`.
- Assert validated `--stderr-sink` forwarding for canonical metadata.
- Drop executable-path existence expectations for review retry.
- Keep invalid metadata fail-closed cases.
- Keep `agent launch-codex-exec` coverage unchanged.

### UPDATED: scripts/test-collect-agent-retry.md

Update pinned prose and assertions.

- Use `OUTER_LAUNCHER=agent launch-review` for canonical review retry examples.
- State that the canonical token is non-filesystem metadata.
- State that retired review launcher metadata fails closed after cutover.
- State that review retry replays through the Python launcher and is not executed directly.

### UPDATED: python/plan_quality.py

Retarget plan revise waterfall launchers.

- Default Codex launcher argv prefix:
  - `sys.executable`
  - `python/cli.py`
  - `agent`
  - `launch-review`
  - `--tool`
  - `codex`
- Default Cursor launcher argv prefix:
  - `sys.executable`
  - `python/cli.py`
  - `agent`
  - `launch-review`
  - `--tool`
  - `cursor`
- Preserve `LARCH_TEST_LAUNCH_CODEX_REVIEW` and `LARCH_TEST_LAUNCH_CURSOR_REVIEW`.
- When either override is set, replace only the launcher executable prefix.
- Still append `--tool <tier>` after the override.
- Do not treat the env var as the full argv list.

### UPDATED: python/test_plan_quality.py

Update revise-waterfall launcher tests.

- Cover default Codex launcher argv prefix.
- Cover default Cursor launcher argv prefix.
- Cover single fake executable overrides from `LARCH_TEST_LAUNCH_CODEX_REVIEW` and `LARCH_TEST_LAUNCH_CURSOR_REVIEW`.
- Assert overrides replace the full default executable prefix.
- Assert the `--tool <tier>` suffix is still appended after the override.
- Assert tests never invoke the real launcher when overrides are set.

### UPDATED: python/plan_scout.py

Retarget dynamic scout Cursor launch.

- Replace single-path default with an argv-prefix default:
  - `sys.executable`
  - `python/cli.py`
  - `agent`
  - `launch-review`
  - `--tool`
  - `cursor`
- Preserve `SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_REVIEW_SH` as the only override hook.
- Treat `SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_REVIEW_SH` as a single fake executable override for tests.
- Do not add `SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_REVIEW_CMD`.
- Do not introduce a new scout launcher configuration contract.
- Add tests that prove the default does not exec a filename containing spaces.

### UPDATED: python/voting.py

Retarget generated review retry and voter launcher argv to `python/cli.py agent launch-review`.

Use `agent launch-review --tool codex` in parse-rate labels and asserted diagnostics.

Keep intentionally generic user-facing labels only when they are not path references.

### UPDATED: python/test_plan_scout.py

Update stubs and expectations for the Python launcher command shape.

Add argv-prefix default coverage.

Cover `SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_REVIEW_SH` as the only override.

Assert no `SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_REVIEW_CMD` behavior is added.

### UPDATED: python/test_voting.py

Update fake launcher setup and expected argv/labels for `agent launch-review`.

### UPDATED: scripts/test-dispatch-code-voters.sh

Retarget parse-rate and voter launcher expectations.

- Expect `agent launch-review --tool codex` where labels now include it.
- Update stub launcher hooks to match the Python launcher argv shape.
- Keep codex-exec coverage unchanged.

### UPDATED: scripts/test-dispatch-code-voters.md

Update pinned expected labels if present.

### UPDATED: python/test_lint_codex_exec_auth.py

Update allowlist expectations after retiring the review shell launcher.

### UPDATED: python/lint_codex_exec_auth.py

Remove the retired review shell launcher from the shell allowlist.

Keep `python/agents.py` as the Python allowlisted raw `codex exec` surface.

### UPDATED: scripts/test-token-vendor-scrapers.sh

Retarget the review launch invocation to:

- `python3 "$REPO_ROOT/python/cli.py" agent launch-review`

Keep the rest of the harness unchanged.

### REWRITTEN: retired review shell launcher

Delete the shell launcher file.

No shell shim should remain.

Collector retry rejects retired review launcher metadata after cutover.

### REWRITTEN: retired review launcher contract doc

Delete the contract doc.

Move current contract details into docs and pytest names.

### REWRITTEN: retired review shell harness

Delete the shell harness after `python/test_launch_review.py` covers parity.

### REWRITTEN: retired review shell harness doc

Delete the harness doc.

### UPDATED: Makefile

Remove shell harness targets for review launch.

Remove all per-section review launch harness targets, including:

- `test-launch-review-cursor-core`
- `test-launch-review-cursor-retry`
- `test-launch-review-codex`

Remove those targets from shard prerequisites.

Wire review-launcher shard coverage to `python3 -m pytest python/test_launch_review.py`, either directly or through a single Python-backed Make target.

Do not rebalance shards unless required by shard coverage checks.

Ensure `py-test` covers `python/test_launch_review.py`.

### UPDATED: agent-lint.toml

Remove exclusions for deleted review shell harness files.

Update comments that mention the retired launcher.

### UPDATED: scripts/test-harness-shards-coverage.md

Remove deleted review harness carve-out prose.

Document the Python pytest replacement for review launcher coverage.

### UPDATED: scripts/test-harness-shards-coverage.sh

Remove deleted review harness carve-outs if present.

Remove references to per-section review launch shell harness targets.

Accept the new Python-backed review launcher coverage target or direct pytest command.

### UPDATED: python/migrated-scripts.tsv

Append retired surfaces with the issue number for this migration piece.

This manifest is the only tracked file allowed to contain exact retired repo-relative path literals.

### UPDATED: docs/external-reviewers.md

Replace active shell review launcher references with `python/cli.py agent launch-review --tool codex|cursor`.

Keep auth scope meaning unchanged.

### UPDATED: docs/configuration-and-permissions.md

Update:

- Codex auth inventory.
- `LARCH_TOKEN_BUDGET_CAP_REVIEW` behavior inside `python/cli.py agent launch-review`.
- Cursor empty-result retry variable description.
- Cursor launch jitter description.

Make clear these apply inside `python/cli.py agent launch-review`.

### UPDATED: docs/linting.md

Update:

- `codex exec` allowlist row.
- `test-collect-agent-retry` description.
- Cursor implementer argv parity source.
- Deleted review shell harness references.
- Python pytest replacement for review launcher parity.

### UPDATED: docs/installation-and-setup.md

Replace active shell review launcher references with `python/cli.py agent launch-review`.

Avoid exact retired-path literals outside the migration manifest.

### UPDATED: docs/run-logs.md

Replace active review launcher references with `agent launch-review`.

Mention that review launch failures can log through implement or design execution-issues context.

Avoid exact retired-path literals outside the migration manifest.

### UPDATED: docs/vendor-agent-diagnostics-audit.md

Replace active shell review launcher references with `python/cli.py agent launch-review`.

Keep historical notes only without exact retired-path literals.

### UPDATED: SECURITY.md

Update review delegation and retry metadata sections.

- Replace active shell review launcher references with `python/cli.py agent launch-review --tool ...`.
- Update retry metadata to `OUTER_LAUNCHER=agent launch-review`.
- State that the canonical review retry token is not a filesystem path.
- State that retired review launcher metadata fails closed after cutover.
- State that review retry replays through the Python launcher.
- Preserve security claims:
  - Codex review uses `codex exec --sandbox read-only`.
  - Cursor review uses `cursor agent -p --trust --mode ask`.
  - dirty-tree sidecar remains a post-run detector.
  - Cursor dirty-tree sidecars preserve baseline path streams.
  - invalid outer metadata fails closed.

### UPDATED: AGENTS.md

Replace active shell review launcher references with `python/cli.py agent launch-review`.

Avoid exact retired-path literals outside the migration manifest.

### UPDATED: .claude/rules/external-tool-launcher-parity.md

Retarget review launcher parity guidance to `python/agents.py` and `python/test_launch_review.py`.

Update frontmatter `paths:` so edits to Python review launcher surfaces inject the rule:

- `python/agents.py`
- `python/test_launch_review.py`
- `python/cli.py`

Remove active retired shell launcher and harness path triggers.

### UPDATED: .claude/rules/launcher-argv-test-coverage.md

Retarget review launcher argv coverage guidance to `python/test_launch_review.py`.

Update frontmatter `paths:` so edits to Python review launcher surfaces inject the rule:

- `python/agents.py`
- `python/test_launch_review.py`
- `python/cli.py`

Remove active retired shell launcher and harness path triggers.

### UPDATED: .gitleaks.toml

Update allowlist comments or paths that mention deleted review launcher files.

Do not weaken secret scanning.

### UPDATED: skills/design/references/brainstorm.md

Retarget representative external launch snippets to:

- `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" agent launch-review`

### UPDATED: skills/design/references/plan-review.md

Replace launch-failure capture references with `python/cli.py agent launch-review`.

### UPDATED: skills/shared/voting-protocol.md

Retarget launcher references to `agent launch-review`.

### UPDATED: skills/implement/scripts/test-cursor-implementer.md

Update references that compare Cursor implementer behavior against the retired review launcher.

Point review-specific behavior to `python/agents.py` and `python/test_launch_review.py`.

### UPDATED: scripts/lib-codex-launcher-common.md

Remove the retired review shell launcher as an active caller.

Point edit-in-sync notes to `python/agents.py` and `python/test_launch_review.py`.

### UPDATED: scripts/lib-cursor-launcher-common.md

Remove the retired review shell launcher as an active caller.

Keep implementer launcher references.

Point review-launcher behavior to `python/agents.py`.

### UPDATED: scripts/lib-external-launcher-common.md

Update doc comments for outer metadata and Codex auth inventory if needed.

Do not remove shell functions still used by implementer launchers.

### UPDATED: scripts/test-lib-external-launcher-common.sh

Update auth inventory and metadata assertions.

- Replace expected review launcher inventory strings with `python/cli.py agent launch-review --tool codex`.
- Update review metadata fixtures to `OUTER_LAUNCHER=agent launch-review`.
- Keep implementer launcher expectations unchanged.

### UPDATED: scripts/lib-cursor-auth.md

Update caller inventory and test guidance.

Point review-launcher coverage to `python/test_launch_review.py`.

### UPDATED: scripts/snapshot-untracked.md

Remove review launcher as a shell snapshot caller if the Python port no longer shells through that script directly.

Mention that review dirty-tree detection still preserves NUL untracked snapshot and baseline path-list semantics through Python helpers.

Do not suggest replacing this flow with checkpoint behavior.

### UPDATED: scripts/dispatch-plan-voters.md

Update per-tool failure comments to reference `agent launch-review`.

### UPDATED: scripts/dispatch-with-waterfall.md

Update Cursor same-line narration note to reference `agent launch-review`.

### UPDATED: scripts/collect-agent-results.md

Update retry eligibility text.

- Document `OUTER_LAUNCHER=agent launch-review`.
- Document that the canonical token is not an executable path.
- Document replay through `python/cli.py agent launch-review`.
- Document that retired review launcher metadata fails closed after cutover.

### UPDATED: scripts/launch-codex-implement.md

Replace active review-launcher comparison references with `python/cli.py agent launch-review`.

Keep implementer-specific content unchanged.

### UPDATED: scripts/launch-cursor-implement.md

Replace active review-launcher comparison references with `python/cli.py agent launch-review`.

Keep implementer-specific content unchanged.

### UPDATED: scripts/lib-dirty-tree-sidecar.sh

Remove comments that claim sharing with the retired review shell launcher.

Keep code intact if still used elsewhere or by Python for baseline parity.

Keep baseline path stream documentation accurate.

### UPDATED: scripts/lib-codex-launcher-common.sh

Update comments only if they mention the retired review shell launcher.

Keep wrappers if still used by other shell launchers.

### UPDATED: scripts/lib-cursor-launcher-common.sh

Update comments only if they mention the retired review shell launcher.

Keep wrappers if still used by other shell launchers.

### UPDATED: scripts/lib-external-launcher-common.sh

Update comments only if they mention the retired review shell launcher.

Keep wrappers if still used by other shell launchers.

## Stale-reference sweep

Run a targeted tracked-file sweep for:

- retired review shell launcher path, constructed as path components
- active shell review launch invocations
- retired review shell harness path, constructed as path components
- deleted review harness target names
- per-section review launch harness shard prerequisites

Update active references to `python/cli.py agent launch-review` or `agent launch-review`.

Keep exact retired repo-relative path literals only in `python/migrated-scripts.tsv`.

Expected sweep targets include:

- `AGENTS.md`
- `.claude/rules/external-tool-launcher-parity.md`
- `.claude/rules/launcher-argv-test-coverage.md`
- `.gitleaks.toml`
- `docs/installation-and-setup.md`
- `docs/run-logs.md`
- `docs/vendor-agent-diagnostics-audit.md`
- `skills/design/references/plan-review.md`
- `skills/implement/scripts/test-cursor-implementer.md`
- implementer launcher docs
- shell library comments
- shell harness fixtures and docs that assert launcher names
- Makefile shard prerequisites
- shard coverage docs and checks

## Edge cases

- Prompt sidecar replay must preserve exact compact sentinel format.
- Sentinel replay must fail closed on missing `KIND`, `AGENT_FILE`, `MODE`, or `HASH`.
- SHA mismatch must fail closed.
- Cursor retry must not prepend the strict preamble more than once.
- `--description-text` must force full prompt sidecar writes.
- Token budget cap must write `.done`, exit 0, and skip vendor launch.
- `LARCH_TOKEN_BUDGET_CAP_REVIEW` must provide the same cap behavior when the flag is absent and the env value is a positive integer.
- Invalid `LARCH_TOKEN_BUDGET_CAP_REVIEW` values must not trigger cap-hit behavior.
- `IMPLEMENT_TMPDIR/session-id` must win over `DESIGN_TMPDIR/session-id`.
- `DESIGN_TMPDIR/session-id` must bind token sessions for standalone design review launches.
- Codex auth setup failure must preserve shell process exit 0 behavior.
- Codex auth setup failure must preserve static clean read-only dirty-tree behavior.
- Codex model-args preflight failure must write unknown dirty-tree status.
- Cursor auth/model preflight failures must write unknown dirty-tree status.
- Design-only launch failures must still reach `DESIGN_TMPDIR/execution-issues.md`.
- Implement launch failures must still stage vendor diagnostics for vendor-failure batches.
- Codex read-only runs should not run a mutable post-run scan.
- Codex finally behavior must write dirty-tree and promote `.done` after metadata and usage.
- Cursor terminal order must be metadata, trap, JSON post-processing, dirty-tree, `.done`.
- Cursor post-run dirty-tree detection must remain baseline-based.
- Cursor dirty sidecars must include path streams consumed by recovery.
- Cursor baseline capture must preserve pre-launch NUL untracked snapshot contract.
- Cursor baseline capture and emission must use Python git/dirty-tree helpers, not checkpoint behavior.
- Pre-existing worktree dirt must not be treated as reviewer-created dirt.
- Retry metadata is tamperable. Keep fail-closed gates before replay.
- `OUTER_LAUNCHER=agent launch-review` is a canonical token, not a filesystem path.
- Retired review launcher metadata must fail closed after cutover.
- Collector retry must forward validated `--stderr-sink`.
- Existing test override env vars may point to a single fake executable. Preserve that behavior where tests depend on it.
- Do not add a new scout launcher override env var.
- Dynamic launcher defaults must be argv-prefix lists.
- Cursor auth must preserve keychain preread and environment normalization.
- Codex add-dir validation must reject unsafe canonicalization cases.
- Per-launch temp homes and config dirs must not be shared across parallel launches.
- Exact retired repo-relative path literals outside the migration manifest can fail retired-script lint.

## Failure modes

- Retrying through inner `CMD_JSON` would skip prompt reconstruction and launcher post-processing.
- Treating `agent launch-review` as an executable path would reject valid retry metadata.
- Accepting retired review launcher metadata would expand a tamperable retry surface after cutover.
- Accepting arbitrary legacy launcher paths would weaken retry metadata validation.
- Omitting `--stderr-sink` on retry would break diagnostics parity.
- Ignoring `LARCH_TOKEN_BUDGET_CAP_REVIEW` would launch vendors after operators configured a review cap.
- Ignoring `DESIGN_TMPDIR/session-id` would lose token-session attribution for design review launches.
- Logging only to implement execution issues would drop design launch-failure records.
- Skipping vendor diagnostics staging would break implement failure triage batches.
- Adding a new scout launcher override would create scope beyond bash parity.
- Using auth-only retry helpers without review transient loops would regress quota, transient, and Cursor empty-result behavior.
- Locking only auth retries would allow concurrent vendor spawns during transient or empty-result retries.
- Bypassing `run_external_agent` would drop `.meta`, `.inner.done`, timeout, and stall contracts.
- Replacing Cursor baseline dirty-tree detection with checkpoint-only detection would cause false positives.
- Reimplementing Cursor dirty-tree git logic ad hoc could miss baseline path-stream contracts.
- Dropping Cursor path streams would break recovery.
- Deleting the shell launcher before all runtime references are retargeted would break review callers.
- Leaving per-section shell harness targets in Makefile shards would break shard prerequisites.
- Omitting Python rule path globs would stop launcher argv reminders from firing on the new review surfaces.
- Cursor JSON post-processing can corrupt output if extraction is not atomic.
- Cursor degraded-response behavior can change if the validator gate is skipped.
- Codex config TOML can break if strict instructions contain `'''`.
- Removing shell harness Makefile targets can break shard coverage metadata.
- Leaving exact retired-path literals outside the manifest can fail `lint-retired-scripts`.

## Testing strategy

Run focused pytest first:

- `python3 -m pytest python/test_launch_review.py`
- `python3 -m pytest python/test_agents.py python/test_plan_quality.py python/test_plan_scout.py python/test_voting.py python/test_lint_codex_exec_auth.py`

Run affected shell harnesses that still exist:

- `make test-dispatch-with-waterfall`
- `make test-dispatch-code-voters`
- `make test-collect-agent-retry`
- `make test-token-vendor-scrapers`
- `make test-lib-cursor-auth`
- `make test-lib-external-launcher-common`
- `make test-cursor-implementer`

Run migration and lint checks:

- `make py-lint`
- `make py-test`
- `make lint-codex-exec-auth`
- `make lint-retired-scripts`
- `bash scripts/relevant-checks.sh`

If `SECURITY.md` changed, include the security-relevant note in the PR summary.
## Acceptance

- [ ] `python/cli.py agent launch-review --tool codex` and `--tool cursor` accept all flags from `scripts/launch-review.sh` and produce the same sidecar contract.
- [ ] `OUTER_LAUNCHER=agent launch-review` is written in `.meta` for every review launch.
- [ ] `LARCH_PROMPT_SENTINEL=1` compact hash sidecar written for `--agent-file` Codex launches without `--description-text`; hash mismatch fails closed.
- [ ] `scripts/dispatch-with-waterfall.sh` and `scripts/collect-agent-results.sh` retry path retargeted to `python3 cli.py agent launch-review`.
- [ ] `scripts/launch-review.sh`, `scripts/launch-review.md`, `scripts/test-launch-review.sh`, `scripts/test-launch-review.md` deleted.
- [ ] `python/test_launch_review.py` passes: parser, sidecars, preflight bundles, retries, post-processing, dirty-tree coverage.
- [ ] `python/migrated-scripts.tsv` updated with all 4 retired files.
- [ ] `make lint`, `make py-lint`, `make py-test`, `make lint-codex-exec-auth`, `make lint-retired-scripts`, and `bash scripts/relevant-checks.sh` all pass.

diff_lines: 7480

## Test plan
(no test plan section in plan-file)
