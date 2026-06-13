# test-dispatch-code-voters.sh

Smoke harness for `scripts/dispatch-code-voters.sh`. Stubs every external binary (`launch-claude-subprocess.sh`, `run-external-agent.sh`, `python/cli.py agent wait-reviewers`, `agent-model-args.sh`, `cursor-auth-flags.sh`, `cursor-wrap-prompt.sh`, `append-tool-failure.sh`) so the test runs offline and tests dispatch wiring rather than vendor responses.

The harness unsets `LARCH_EXECUTION_ISSUES_LOG`, `SESSION_ENV_PATH`, and `IMPLEMENT_TMPDIR` at startup so parent `/implement` env vars never leak into test invocations. Tests that assert on issues-log writes set `LARCH_EXECUTION_ISSUES_LOG` explicitly on each individual invocation.

## Coverage

Scenarios plus 3 regression blocks split across 8 `--section` groups for CI shard packing (the 8-group split is pinned by the invariant below):

Every `--section` shard asserts `VOTER_PATHS_FILE` points at a non-empty `code-voter-paths.txt`; `happy` additionally checks paths-file line counts across panel sizes: 3 lines (round 1, both vendors up), 3 lines (round 2), 2 lines (one external down — Claude + the available external), and 1 line (both externals down — Claude only).

- `happy`: all voters available (full 3-judge panel); **shrink-not-backfill when externals are unavailable** — both externals down → Claude-only panel (Voter 2/3 `skipped`, not back-filled, **no** degraded warning, 1-line paths file); exactly one external down → 2-judge panel (the absent vendor `skipped`, the available one launched, no degraded warning); voter1 fails; round-2 3-judge parity; asserts no `*-vote-output-first-pass.txt` sidecars on the no-retry path; a #3704 parallel-dispatch probe where the Claude CLI stub blocks until the waterfall stub drops a marker file (serialized dispatch fails Voter 1 deterministically — no wall-clock assertion).
- `happy` also covers the #2973 voter `.done` barrier and related regressions: delayed Voter 2/3 output becomes visible before `.done`, and dispatch still waits on the sentinel barrier before final size-based status checks (including real `launch-review.sh` delayed-promotion paths for both Cursor and Codex; FINDING_1, FINDING_4); an immediate-sentinel path proves the normal `_wait_rc=0` branch survives under `set -e`; a hook case separately proves raw Cursor JSON is still tallied after `.inner.done` promotion (FINDING_2); a Voter 1 launcher-with-late-sentinel fixture proves dispatch waits for the launcher-owned Claude sentinel instead of short-circuiting it with an early synthetic `.done`, and a missing-sentinel timeout path proves dispatch no longer backfills that slot to success (FINDING_3, FINDING_5); timeout rows from `python/cli.py agent wait-reviewers` stdout are surfaced; non-zero external `.done` exit codes fail Voter 2/3 even when their `.txt` files are non-empty (FINDING_19); and a usage-error fixture covers the distinct `_wait_rc!=0` diagnostic branch.
- `edge-and-r3-claude` (scenarios 4-5 + Regression 3 claude case): symlink diff; 2 MB diff; production-shape claude voter parse-rate failure.
- `retry-claude` (scenarios 6-7): claude voter parse-rate retry success (first-pass sidecar present, differs from promoted output); parse-rate retry failure (no sidecar).
- `retry-codex-success` (scenario 8): codex voter parse-rate retry success (first-pass sidecar present, differs from promoted output).
- `retry-cursor` (scenario 9): cursor voter parse-rate retry success (first-pass sidecar present, differs from promoted output).
- `retry-codex-fail-and-fallback`: codex parse-rate retry failure with both vendors up (2/3 degraded, no first-pass sidecar); both-externals-down shrink where the sole Claude judge goes narrative-only (Voter 2/3 `skipped`, no phase3 back-fill output, 0/1 degraded warning).
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

Mirrors `scripts/test-dispatch-plan-voters.sh`: a fresh PLUGIN_ROOT directory is populated with stub scripts that write deterministic outputs/sentinels when a test substitutes `CLAUDE_PLUGIN_ROOT`. The `dispatch-code-voters.sh` harness normally leaves `CLAUDE_PLUGIN_ROOT` unset so `${CLAUDE_PLUGIN_ROOT:-repo-root}` resolves to the real checkout, and `python/cli.py render voter` is exercised from the live tree. Targeted regression fixtures temporarily swap in custom plugin roots for the Voter 2/3 wait barrier, the wait-helper usage-error branch, and the Voter 1 late-sentinel path. The `happy` section asserts the composed prompts include the canonical finding-only OOS clause, the informational-fix guardrails, a `FINDING_N:` example line, and **no** `OOS_N` substring (grammar-conditional plan-vs-code split).
