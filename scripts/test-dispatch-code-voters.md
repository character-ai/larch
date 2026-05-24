# test-dispatch-code-voters.sh

Smoke harness for `scripts/dispatch-code-voters.sh`. Stubs every external binary (`launch-claude-subprocess.sh`, `run-external-agent.sh`, `wait-for-reviewers.sh`, `agent-model-args.sh`, `cursor-auth-flags.sh`, `cursor-wrap-prompt.sh`, `append-tool-failure.sh`) so the test runs offline and tests dispatch wiring rather than vendor responses.

The harness unsets `LARCH_EXECUTION_ISSUES_LOG`, `SESSION_ENV_PATH`, and `IMPLEMENT_TMPDIR` at startup so parent `/implement` env vars never leak into test invocations. Tests that assert on issues-log writes set `LARCH_EXECUTION_ISSUES_LOG` explicitly on each individual invocation.

## Coverage

11 scenarios + 3 regression blocks split across 8 `--section` groups for CI shard packing:

Every `--section` shard asserts `VOTER_PATHS_FILE` points at a non-empty `code-voter-paths.txt`; `happy` additionally checks 3-line vs 2-line paths files for round 1 vs round 2.

- `happy` (scenarios 1-3): all voters available; codex/cursor absent; voter1 fails; asserts no `*-vote-output-first-pass.txt` sidecars on the no-retry path.
- `edge-and-r3-claude` (scenarios 4-5 + Regression 3 claude case): symlink diff; 2 MB diff; production-shape claude voter parse-rate failure.
- `retry-claude` (scenarios 6-7): claude voter parse-rate retry success (first-pass sidecar present, differs from promoted output); parse-rate retry failure (no sidecar).
- `retry-codex-success` (scenario 8): codex voter parse-rate retry success (first-pass sidecar present, differs from promoted output).
- `retry-cursor` (scenario 9): cursor voter parse-rate retry success (first-pass sidecar present, differs from promoted output).
- `retry-codex-fail-and-fallback` (scenarios 10-11): codex parse-rate retry failure (no first-pass sidecar); all-claude fallback parse-rate failure.
- `regressions-r1-r2`: env isolation (Regression 1) + harness-ancestor path guard (Regression 2).
- `regressions-r3-codex`: production-shape codex voter parse-rate failure (Regression 3, codex half).

Invariant: no ungated code may live between the last `fi  # end section:` and the closing `echo "PASS: ..."`. Verify with `grep -c 'if section_runs' scripts/test-dispatch-code-voters.sh` == 8 after any structural edits.

## Invocation

```bash
scripts/test-dispatch-code-voters.sh
```

Run a single section:

```bash
scripts/test-dispatch-code-voters.sh --section happy
```

Exit 0 → pass, exit 1 → at least one assertion failed.

## Stubbing pattern

Mirrors `scripts/test-dispatch-plan-voters.sh`: a fresh PLUGIN_ROOT directory is populated with stub scripts that write deterministic outputs/sentinels when a test substitutes `CLAUDE_PLUGIN_ROOT`. The `dispatch-code-voters.sh` harness leaves `CLAUDE_PLUGIN_ROOT` unset so `${CLAUDE_PLUGIN_ROOT:-repo-root}` resolves to the real checkout — `skills/shared/scripts/render-voter-prompt.sh` is exercised from the live tree. The `happy` section asserts the composed prompts include the canonical finding-only OOS clause, the informational-fix guardrails, a `FINDING_N:` example line, and **no** `OOS_N` substring (grammar-conditional plan-vs-code split).
