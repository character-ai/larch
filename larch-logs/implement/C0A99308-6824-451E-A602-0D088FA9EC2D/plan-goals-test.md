## Goal
Implement issue #4168: [IMPLEMENTING] sh-to-py C1a4: Results collector and retry contracts.

## Implementation Plan
## Plan

## Approach

Make a hard cutover to `python3 python/cli.py agent collect-results`.

Keep the observable collector contract stable:

- stdout record grammar stays unchanged.
- record order stays argv order.
- wait timeout correlation stays index-based.
- retry metadata remains fail-closed.
- `LARCH_QUIET_DISABLE=1` and fd-3 behavior stay compatible with `logging_util.quiet_init()`.
- no shim remains at `scripts/collect-agent-results.sh`.

Use existing Python surfaces where they already own behavior:

- `review_dispatch.wait_reviewers()` for sentinel waits (with caller-controlled emit/diagnostic sinks).
- `review_dispatch._validate_positive_int()` (same path as `wait_reviewers_main`) for positive-timeout validation on the initial wait.
- `review_dispatch.render_failed_agent_stderr_tail()` for redacted stderr tails.
- `retry.is_transient_net_signature()` for transient diagnostics.
- `logging_util.quiet_init()`, `emit()`, and `diagnostic()` for contract output and diagnostics.
- `agents._COLLECTOR_NS_STRONG_HEADER` for non-substantive retry prompt strengthening.
- `python/cli.py agent external-tool-registry --kind external-tools` (or equivalent helper) for `.meta` `TOOL=` allowlist parity with `scripts/external-tool-registry.sh`.
- `python/cli.py` subprocess verbs for launcher replay and validation.

Port failed-agent stderr tail resolution from `scripts/lib-failed-agent-stderr-tail.sh` (`resolve_collector_stderr_tail_file`, `collector_stderr_tail_candidates`, `failed_agent_stderr_signature`) into `python/collect_results.py` or a small shared Python helper colocated with `review_dispatch.py`. Treat that shell library as normative for suffix preference, phase-candidate walk, temp tail materialization from `.launch-stderr`, and signature-based dedup.

Use subprocess seams in the new module so tests can monkeypatch launch, wait, validation, filesystem, and cwd without invoking the deleted shell script.

**Initial wait (shell parity):**

- Before any polling, reject non-positive `--timeout` using the same `_validate_positive_int` rules as `wait_reviewers_main` (`--timeout 0` or non-digit → exit `1`, no `REVIEWER_FILE=` / `STATUS=` stdout, wait error text on stderr).
- Run the initial wait through buffered in-process `wait_reviewers()`: pass captured `emit_fn` and `diagnostic_fn` wrappers that accumulate lines into memory for parsing only.
- On success: consume buffered `TIMEOUT` indices internally; do not relay `DONE`/`TIMEOUT` lines or poll progress dots onto the collector contract stream.
- On failure: relay sanitized buffered diagnostics via `larch_err` / `diagnostic()`, then exit `1` with no reviewer records.
- Parse wait output by `TIMEOUT <idx> <basename>` and correlate by 1-based argv index.

**Retry-phase waits:** use no-op `emit_fn` / `diagnostic_fn` sinks; swallow non-zero wait exit; derive outcomes from sentinel files afterward.

**Outer-launcher replay cwd:** match `scripts/collect-agent-results.sh:810-833`: launch each outer retry in an isolated child context with `subprocess.Popen(..., cwd=validated_workdir)`. Never call `os.chdir()` on the collector process; parallel retries with different workdirs must stay isolated.

## Files to modify/create

### NEW: python/collect_results.py

Implement the collector library and CLI entrypoint.

Add core data structures:

- `CollectorOptions`: parsed flags, timeout, summary mode, validation modes, and output paths.
- `CollectorRecord`: `REVIEWER_FILE`, `TOOL`, `STATUS`, `EXIT_CODE`, optional `STRUCTURED_SIDECAR`, `FAILURE_REASON`, and internal non-substantive retry fields (`NS_RETRY_MODE`, `NS_RETRY_REASON`).
- `RetryMeta`: parsed `.meta` fields.
- `RetryPlan`: retry output, sentinel, timeout, argv, and launch mode.

Implement CLI parsing for all flags. Preserve all argument errors. Build sentinels as `<output>.done`.

Validate `--timeout` with `review_dispatch._validate_positive_int()`. Call `review_dispatch.wait_reviewers()` with buffered capture sinks.

Derive tool in this order:
1. `.meta` `TOOL=` only when it passes the external-tool registry allowlist.
2. basename substring match against registered external tools.
3. `unknown`.

Preserve all status mappings, sentinel handling, failure-reason sanitization, and `derive_ns_retry_reason`.

Implement transient-diagnostic retry with shell parity (requires `.diag` before calling `is_transient_net_signature`).

Implement empty-output retry, substantive validation, structured validation, and non-substantive retry.

After the NS-retry batch settles, unlink any `larch-ns-retry-prompt.*` temp files created by `preserve_and_publish_ns_retry` (matching `scripts/collect-agent-results.sh:1472` NS_RETRY_PROMPTS cleanup).

Implement failed-agent stderr tail resolution ported from `scripts/lib-failed-agent-stderr-tail.sh`.

Emit final records with blank lines between reviewers. Implement `--summary-only` suppression.

### NEW: python/test_collect_results.py

Replace the retired bash harness coverage with pytest. Cover all cases listed in the testing strategy.

### UPDATED: python/cli.py

Register `("agent", "collect-results"): ("collect_results", "collect_results_main")`.

### UPDATED: scripts/dispatch-with-waterfall.sh

Replace both collector calls with `python3 "$SCRIPT_DIR/../python/cli.py" agent collect-results`.

### UPDATED: scripts/dispatch-with-waterfall.md

Update prose to name `python/cli.py agent collect-results`.

### UPDATED: skills/design/scripts/design-step1d5.sh

Replace the brainstorm collector invocation with `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" agent collect-results`.

### UPDATED: python/legacy_review_shell/collect-findings.sh

Replace Step 3a collection with `python3 "$PLUGIN_ROOT/python/cli.py" agent collect-results`.

### UPDATED: Makefile

Retarget `test-collect-agent-results` to `cd python && $(PYTHON) -m pytest test_collect_results.py`. Remove deleted harness targets.

### UPDATED: scripts/relevant-checks.sh

Route `python/collect_results.py`, `python/test_collect_results.py`, `python/cli.py`, and collector callers to `test-collect-agent-results`.

### UPDATED: scripts/test-review-structure.sh

Update pin 13 to look for `agent collect-results` in `python/legacy_review_shell/collect-findings.sh`.

### UPDATED: scripts/test-research-structure.sh

Update collector command pins to the Python CLI path.

### UPDATED: scripts/test-dispatch-with-waterfall.sh

Retarget direct collector invocations to `python3 python/cli.py agent collect-results`.

### UPDATED: scripts/test-design-multi-round-integration.sh

Replace the stubbed `collect-agent-results.sh` fixture with a `python/cli.py agent collect-results` stub path.

### UPDATED: scripts/test-prompt-template-invariants.sh

Move `NS_STRONG_HEADER` assertions away from the deleted shell script to `python/collect_results.py` or `python/agents.py`.

### UPDATED: scripts/test-prompt-template-invariants.md

Update the collector row to name `python/collect_results.py` or `python/agents.py`.

### UPDATED: scripts/test-ci-wait-exit-trap.md

Update any reference to `collect-agent-results.sh` that pins the CI wait exit-trap behavior.

### UPDATED: python/test_review_dispatch.py

Remove the subprocess passthrough test that shells out to `scripts/collect-agent-results.sh`.

### UPDATED: python/migrated-scripts.tsv

Add retired collector paths.

### UPDATED: agent-lint.toml

Remove Makefile-only excludes for deleted collector harnesses.

### UPDATED: .claude/rules/external-tool-launcher-parity.md

Replace the collector path in `paths:` and prose with `python/collect_results.py` and `python/cli.py agent collect-results`.

### UPDATED: SECURITY.md

Replace the retired collector script reference with `python/cli.py agent collect-results`.

### UPDATED: docs/external-reviewers.md

Update collector behavior and flag documentation.

### UPDATED: docs/linting.md

Replace deleted harness documentation with `test-collect-agent-results`.

### UPDATED: docs/configuration-and-permissions.md

Update collector dedup prose.

### UPDATED: scripts/ci-wait.md

Update sentinel-reader prose to name `python/cli.py agent collect-results` and `python/cli.py agent wait-reviewers`.

### UPDATED: scripts/external-tool-registry.md

Update sourced-by and related prose.

### UPDATED: scripts/external-tool-registry.sh

Update comments that name the retired collector script.

### UPDATED: scripts/lib-codex-launcher-common.md

Update retry metadata prose.

### UPDATED: scripts/lib-external-launcher-common.md

Update retry metadata prose.

### UPDATED: scripts/lib-failed-agent-stderr-tail.md

Update collector dedup prose.

### UPDATED: scripts/lib-net.md

Update edit-in-sync prose. State that collector transient classification now uses `python/retry.py`.

### UPDATED: scripts/lib-quiet.md

Update examples that name the retired collector script.

### UPDATED: scripts/lib-cursor-auth.sh

Update the portability comment that mirrors the retired script.

### UPDATED: skills/design/SKILL.md

Replace the Step 2a negative reference with `agent collect-results`.

### UPDATED: skills/design/references/plan-review.md

Replace collection examples with the Python CLI.

### UPDATED: skills/design/references/brainstorm.md

Replace brainstorm collection examples with the Python CLI.

### UPDATED: skills/research/references/research-phase.md

Replace research collection examples with the Python CLI.

### UPDATED: skills/research/references/validation-phase.md

Replace validation collection examples with the Python CLI.

### UPDATED: skills/review/references/heavy-worker.md

Replace the foreground Bash-tool wording with a foreground collector CLI call.

### UPDATED: skills/shared/external-reviewers.md

Replace shared collector examples with the Python CLI.

### UPDATED: skills/shared/voting-protocol.md

Replace collector prose with the Python CLI name.

### UPDATED: skills/shared/dialectic-protocol.md

Replace external judge collection examples with the Python CLI.

### UPDATED: scripts/collect-agent-results.sh

Delete this file after `python/test_collect_results.py` covers its behavior.

### UPDATED: scripts/collect-agent-results.md

Delete this file.

### UPDATED: scripts/test-collect-agent-results.sh

Delete this harness after pytest parity exists.

### UPDATED: scripts/test-collect-agent-results.md

Delete this harness doc.

### UPDATED: scripts/test-collect-agent-retry.sh

Delete this harness after pytest parity exists.

### UPDATED: scripts/test-collect-agent-retry.md

Delete this harness doc.

### UPDATED: scripts/test-collect-agent-bash32.sh

Delete this harness.

### UPDATED: scripts/test-collect-agent-bash32.md

Delete this harness doc.

## Edge cases

- Duplicate basenames must remain correlated by argv index.
- `STATUS=OK` plus empty `FAILURE_REASON` is success. `EXIT_CODE=0` alone is not success.
- `cap_hit` remains terminal for waterfall phase collection.
- `CURSOR_DEGRADED_RESPONSE` remains equivalent to `CURSOR_EMPTY_RESPONSE`.
- Invalid initial `.done` values coerce to `EXIT_CODE=99`.
- Retry metadata fails closed for malformed JSON, missing timeout, unknown tool, bad launcher kind, bad sandbox, bad prompt sidecar, bad workdir, and bad add-dir JSON.
- `--summary-only` must suppress `FAILURE_REASON` and `STRUCTURED_SIDECAR`.
- Stderr-tail dedup runs after retries and validation settle.
- Python JSON replaces `jq`.
- Bash 3.2-specific implementation coverage is deleted, not recreated.
- Transient retry requires `.diag` before calling `is_transient_net_signature`.
- NS-retry temp prompts (`larch-ns-retry-prompt.*`) are unlinked after the NS-retry batch settles.
- Outer-launcher cwd isolation uses `subprocess.Popen(..., cwd=validated_workdir)` — never `os.chdir()`.

## Failure modes

- Initial wait setup or wait value validation exits `1` and emits no reviewer records.
- A reviewer wait timeout emits `SENTINEL_TIMEOUT`.
- A process exit `124` emits `TIMED_OUT`.
- A non-zero process exit emits `FAILED`.
- Empty output without usable retry remains `EMPTY_OUTPUT`.
- Invalid retry metadata emits `EMPTY_OUTPUT` with `EXIT_CODE=99`.
- Retry launch without a retry sentinel emits `EMPTY_OUTPUT` with `EXIT_CODE=99`.
- Retry non-zero exit propagates the retry sentinel exit code.
- Substantive validation failure stays `NOT_SUBSTANTIVE` if non-substantive retry fails.
- Structured validation success without a publishable sidecar must not emit a false successful sidecar path.

## Testing strategy

Run focused Python tests first:

```bash
cd python && python3 -m pytest test_collect_results.py test_review_dispatch.py
```

Run affected harnesses:

```bash
make test-collect-agent-results
make test-dispatch-with-waterfall
make test-review-structure
make test-research-structure
make test-prompt-template-invariants
make test-design-multi-round-integration
make test-relevant-checks
make lint-retired-scripts
```

Run full relevant checks:

```
bash scripts/relevant-checks.sh
```

Before deleting the shell collector, the implementer may run the old three harnesses once while they still exist to compare behavior. After deletion, rely on `python/test_collect_results.py`.

Run `make lint-retired-scripts` as a pre-merge gate after the stale-reference sweep.

## Acceptance criteria

1. `python3 python/cli.py agent collect-results --timeout <N> ...` emits the same stdout block grammar as the retired script.
2. All live callers use the Python CLI directly.
3. No shim remains at `scripts/collect-agent-results.sh`.
4. The three bash harnesses are replaced by `python/test_collect_results.py`.
5. Retry metadata remains fail-closed, including outer-metadata precedence, `cmd_json_requires_outer_launcher`, and test-hook env stripping.
6. Duplicate basename timeout correlation is index-based.
7. `.meta` tool derivation uses the external-tool registry allowlist.
8. Transient retry requires `.diag` and does not spuriously match timeout-only text.
9. Structured NS retry preserves sidecar publish and `CURSOR_EMPTY_RESPONSE` downgrade behavior.
10. Failed-agent stderr tail resolution matches `lib-failed-agent-stderr-tail.sh`.
11. Empty-output and NS retries launch in parallel and settle with one batch `wait_reviewers` per retry class.
12. `derive_ns_retry_reason` and `NS_RETRY_REASON` `.meta` annotation match shell (`C_NSR_REASON`, structured `JSON_PARSE_FAIL`).
13. `collect-findings.sh` preserves subshell `unset LARCH_QUIET_*` + `LARCH_QUIET_DISABLE=1` around the collector CLI.
14. NS-retry temp prompt files (`larch-ns-retry-prompt.*`) are unlinked after the NS-retry batch settles.
15. Outer-launcher cwd isolation uses `subprocess.Popen(..., cwd=validated_workdir)` — no `os.chdir()`.
16. `--timeout 0` exits `1` before any polling (bad-timeout parity).
17. Initial wait buffered emit/diagnostic wrappers do not relay progress dots or `DONE` lines to collector contract stdout.
18. `--timeout 0` and `--timeout abc` do not call `wait_reviewers()` (pre-validation exit).
19. Retry-phase waits use no-op sinks (no relay to collector stdout).
20. Outer-launcher retry `cwd` is set to `validated_workdir`, not the collector process cwd.
21. Initial wait failure (`wait_reviewers` non-zero) relays sanitized buffered diagnostics, then exits `1` with no reviewer records (issue #1188 parity).
22. Retry wait failure exits via non-zero sentinel without relay, not via `wait_reviewers` non-zero exit.
23. Test-hook env stripping (`LARCH_COLLECT_RESULTS_*`) strips env vars used by integration tests before launching subprocesses.
24. Meta `.meta` fallback works when `TOOL=` is absent.
25. Initial-wait `_validate_positive_int` is exercised by a dedicated pytest case (bad-timeout exit-1 before any polling).
26. `SECURITY.md` is updated because external reviewer retry and degradation handling remain security-relevant.

## Acceptance

Gate C approved.

diff_lines: 6960

## Test plan
(no test plan section in plan-file)
