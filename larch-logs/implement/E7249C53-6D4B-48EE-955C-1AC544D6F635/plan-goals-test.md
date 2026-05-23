## Goal
Fix test harnesses to unset inherited LARCH_EXECUTION_ISSUES_LOG and related env vars, preventing synthetic test fixtures from leaking into parent /implement run-logs

## Implementation Plan
## Plan

### Affected files (concrete paths)

- `skills/review/scripts/test-aggregate-findings.sh` — primary leak source (already has `unset LARCH_AGGREGATOR_DISABLED || true` at top; extend the unset list).
- `scripts/test-launch-review.sh` — secondary leak source (the `Step review Step 2 — codex-review failed (exit 7 …)` synthetic headers in audit #2615 trace here).
- `scripts/test-append-tool-failure.sh` — same family; emits the synthetic retry-header verbatim.

No production-code changes in this scope (see Closed decisions below for the deferred defensive-default option).

### Sequencing (ordered steps)

1. **Edit `skills/review/scripts/test-aggregate-findings.sh`**: locate the existing `unset LARCH_AGGREGATOR_DISABLED || true` line near the top of the script (currently around the same block as `set -euo pipefail`). Immediately after that line, append:

   ```bash
   unset LARCH_EXECUTION_ISSUES_LOG SESSION_ENV_PATH IMPLEMENT_TMPDIR || true
   ```

   This block runs once at script entry; subsequent per-case test fixtures continue to set those vars explicitly where they need them (e.g., the existing `LARCH_EXECUTION_ISSUES_LOG="$EX/execution-issues.md"` overrides in this harness).

2. **Edit `scripts/test-launch-review.sh`**: same unset prelude after `set -euo pipefail`. Use the same one-line `unset … || true` shape so future grep audits can find the pattern uniformly.

3. **Edit `scripts/test-append-tool-failure.sh`**: same unset prelude.

4. **Add a regression test case** to `skills/review/scripts/test-aggregate-findings.sh` (append a new section before the existing `echo "All aggregate-findings harness assertions passed."` final line). The case must:
   - Create a sentinel path: `SENTINEL=/tmp/larch-test-env-leak-$$.md` and ensure it doesn't exist (`rm -f "$SENTINEL"`).
   - Export `LARCH_EXECUTION_ISSUES_LOG="$SENTINEL"` deliberately (overriding the harness's unset prelude for this one case).
   - Invoke `aggregate-findings.sh --review-tmpdir "$TMP/leak-probe" …` against synthetic dispatch-failure inputs that produce at least one "findings aggregator" warning.
   - Assert `! [[ -f "$SENTINEL" ]] || [[ ! -s "$SENTINEL" ]]` — the sentinel must not exist OR must be empty. If aggregate-findings.sh wrote to `LARCH_EXECUTION_ISSUES_LOG` despite the explicit `--review-tmpdir`, this assertion fails.
   - Clean up: `rm -f "$SENTINEL"`.

   **Note**: this regression test pins the *future* defensive-default behavior. It will FAIL against the current `aggregate-findings.sh:71-81` precedence (env var wins over `--review-tmpdir`). Acceptance bullet 4 below resolves this.

5. **Decision point (item from Closed decisions)**: choose between two acceptance shapes for the regression test:
   - **Shape A** (test-harness fix only): the regression test asserts the harness behavior — i.e., that *when run via `make test-aggregate-findings`*, no sentinel leaks. This passes with steps 1–3 alone, but doesn't protect against a future caller forgetting to unset. Implement Shape A unless the operator picks Shape B during clarify.
   - **Shape B** (test-harness fix + production defensive default): also flip `aggregate-findings.sh:71-81` `execution_issues_log()` precedence so `--review-tmpdir` wins over `LARCH_EXECUTION_ISSUES_LOG` when both are present (env var becomes last-resort fallback). The regression test in step 4 then passes regardless of harness-side unset hygiene. Shape B is broader and changes production semantics for legitimate callers that pass both; defer to Shape A unless the operator explicitly opts in via clarify.

   **Default decision**: **Shape A** (test-harness fix only). Rationale: Shape B's production semantics shift could surprise callers who rely on `LARCH_EXECUTION_ISSUES_LOG` precedence; Shape A is the minimal fix that resolves the observed leak. If operator wants Shape B, file a follow-up issue.

6. **Run `make test-aggregate-findings`** (or the broader `make test-harnesses-8` shard) and confirm green. Run `make lint` to confirm no incidental regressions.

7. **Manual verification**: re-run a quick end-to-end probe — execute one of the three harnesses with `LARCH_EXECUTION_ISSUES_LOG=/tmp/leak-probe.md` set in the outer env, observe whether `/tmp/leak-probe.md` gets written. Before the fix: it gets written. After the fix: it stays empty/absent.

### Breaking changes

- **None for plugin consumers.** The change is internal to test harnesses (`scripts/test-*.sh`, `skills/review/scripts/test-*.sh`) which are not part of the runtime surface shipped to plugin consumers per `AGENTS.md` "Runtime surface" definition.
- **None for plugin developers running `make lint`/`make test-harnesses` locally.** The unset prelude only clears env vars at script entry; per-case explicit settings within the harness still work as before. Operators who deliberately set `LARCH_EXECUTION_ISSUES_LOG` before invoking the test harness from a shell will see that override discarded — which is exactly the intended fix.

### Closed decisions

- **Decision: Shape A over Shape B for default scope.** Production-code `execution_issues_log()` precedence stays as-is; only the test harnesses change. Rationale captured in step 5 above.
- **Decision: three harnesses (not more).** Audit #2615 evidence pins the leak shape to `test-aggregate-findings.sh` paths and `test-launch-review.sh` / `test-append-tool-failure.sh` synthetic headers. Other test scripts that touch execution-issues.md (e.g., `scripts/test-refresh-execution-issues.sh`, `scripts/test-flush-execution-issues.sh`) use their own controlled tmpdir and do not exhibit the leak signature in audited runs.
- **Decision: regression test lives in `test-aggregate-findings.sh` only (one harness, not three).** The leak mechanism is shared, so one regression case proves the family-level invariant; duplicating it across three harnesses adds maintenance cost without proportional coverage.
- **Decision: do not change `aggregate-findings.sh::execution_issues_log()`** in this issue. The defensive-default flip belongs in a separate follow-up that audits all legitimate callers of `LARCH_EXECUTION_ISSUES_LOG` first.

## Acceptance

- [ ] `bash skills/review/scripts/test-aggregate-findings.sh` passes (including the new regression case from step 4).
- [ ] `make test-aggregate-findings` and `make test-harnesses-8` pass green in CI.
- [ ] `make lint` passes (no incidental shellcheck, markdownlint, or agent-lint regressions).
- [ ] Manual verification (step 7): with `LARCH_EXECUTION_ISSUES_LOG=/tmp/leak-probe.md` exported in the shell, running any of the three patched harnesses leaves `/tmp/leak-probe.md` empty/absent.
- [ ] The next `/audit-runs` cycle on `/implement` runs that exercise `make test-harnesses-N` shows zero `findings aggregator: merged output failed validation` entries with `test-*.XXXXXX/` stderr paths in any audited execution-issues.ndjson.
- [ ] CHANGELOG.md gets a one-line entry under `Fixed`: roughly "test-aggregate-findings/test-launch-review/test-append-tool-failure: unset LARCH_EXECUTION_ISSUES_LOG and related vars to prevent synthetic warnings leaking into parent run-log".

## Test plan
(no test plan section in plan-file)
