# larch Python runtime

Mostly-flat `python/` tree for larch's stdlib-only runtime modules (Python ≥ 3.11 for the `/implement` Step 8+ ship driver and `/report-tokens`). The shared leaf layer lives in the `larch/` package: `larch.io`, `larch.errors`, `larch.outcomes`, and the `larch.core` home for the most-depended-on leaf utilities (`proc`, `config`, `logging_util`, `redact`, `retry`, `run_context`). `/implement` Step 8+ uses `python/cli.py ship pr` (delegating to `python/ship.py`). `/report-tokens` is live via `python/cli.py report-tokens analyze` (delegating to `report_tokens_cli.py`); the retired `run-analysis.sh` wrapper has been removed. Linters and pytest are dev/CI-only and are never imported by runtime code.

## Layout

- `larch/` — foundation package for the stdlib-only shared leaf layer; domain modules move in under later packaging children
- `larch/core/config.py` — tunables (exit codes, timeouts, tier order, env-var names)
- `larch/core/proc.py` — injectable subprocess seam
- `larch/errors.py`, `larch/outcomes.py`, `larch/core/run_context.py` — typed errors and run context
- `larch/io.py` — shared text, `KEY=value`, and atomic-write helpers for larch wire files
- `larch/core/logging_util.py` — breadcrumbs + JSONL journal (observability only); `quiet_init()` owns Python stream routing, and `contract_stream()` sends ship-driver JSON to fd 3 after self-initialized quiet
- `larch/core/redact.py`, `larch/core/retry.py` — secret redaction and transient retry helpers
- `rendering.py` — prompt renderers, Mermaid sanitizer, diagrams upserter, and generated-artifact generators now exposed through `python/cli.py` (`render`, `mermaid`, `diagrams`, and `generate` domains).
- `voting.py` — voting, tally, parse-rate, ballot parsing, scoreboard, and focus-area enum CLI surfaces.
- `lint_literal_counts.py`, `lint_consecutive_bash.py`, `lint_no_raw_stderr_after_quiet_init.py`, `check_topology_rule_paths.py` — local lint surfaces exposed as `python/cli.py lint literal-counts`, `python/cli.py lint consecutive-bash`, `python/cli.py lint no-raw-stderr-after-quiet-init`, and `python/cli.py lint topology-rule-paths`.
- `render_session_transcript.py`, `cleanup_implement_logs.py`, `retro_v3_sweep.py` — run-log maintenance surfaces exposed as `python/cli.py run-log render-session-transcript`, `python/cli.py run-log cleanup-implement-logs`, and `python/cli.py run-log retro-v3-sweep`.
- `git.py`, `gh.py`, `agents.py` — typed `git` / `gh` / fixer launcher surfaces
- `version_bump.py` — shared semver classification helpers used by release preparation and Python parity tests.
- `report_tokens_models.py`, `report_tokens_scan.py`, `report_tokens_cost.py`, `report_tokens_render.py`, `report_tokens_plot.py`, `report_tokens_issue.py`, `report_tokens_cli.py` — live `/report-tokens` scan, pricing, render, plot-subprocess, issue-posting, and CLI pipeline.
- `rebase.py` — CI-fix rebase decision and verification surfaces used by the default Python ship driver.
- `checks.py` — local relevant-checks runner and lint-fix loop (Phase 4); local
  fixer dispatch does **not** call `agents.classify_launch_failure` (bash #3207 parity)
- `ci_monitor.py` — live on the default Python Step 8+ path; `python/ship.py` calls it from
  the merge loop after PR creation to poll CI, classify failures, collect failed-job data,
  run the fixer waterfall, and return the GOTO-Rebase signal.
- `design_log_ship.py` — CI-wait (required checks, checks-only) plus bounded failed-run
  rerun and transient-retried squash-admin-merge for design-log PRs; invoked via
  `python/cli.py ship design-log`.
- **Phase 5** (live via default Python ship driver): `run_logs.py`, `tokens.py`, `tracking_issue.py`,
  `pr_body.py`, `push.py`, `pr.py`, `file_oos.py`, `merge.py` — PR/merge/logging ports with split
  `flush_logs_pre` (may commit log batches) vs `flush_logs_post` (tmpdir-only). `merge.py`
  classifies the eight `python/cli.py merge pr` `MERGE_RESULT` literals; driver-only `already_merged` is
  documented in `config.MERGE_RESULT_DRIVER_ALREADY_MERGED` for `flush_logs_pre` skip parity.
  Tool-failure batch capture remains deferred to Phase 7 wiring; bash launchers still own
  `append-tool-failure.sh` calls on the live path.
- `test_rendering.py` — pytest coverage replacing the retired renderer/generator bash harnesses.
- `test_<module>.py` — colocated unit tests; `test_support.py` provides the shared list-queue `RecordingRunner` (with `test_run_logs.py` preserving `git_commits` via a subclass and `test_ci_monitor.py` retaining its keyed runner); `test_stdlib_only.py` enforces stdlib-only imports

## Dependencies

| File | Purpose |
|------|---------|
| `requirements-dev.txt` | ruff, pylint, pyright (Python Lint CI / `make py-lint`) |
| `requirements-test.txt` | pytest only (Python Tests CI / `make py-test`; no Node) |

## Run locally

From the repository root (after `pip install -r python/requirements-dev.txt` and/or
`python/requirements-test.txt`):

```bash
make py-lint   # cd python && ruff check . && pylint -j 0 . && pyright
make py-test   # cd python && pytest
```

`make lint` does not invoke `py-lint` or `py-test`; use those targets explicitly or rely on
CI `python-lint` / `python-tests` jobs. Per-job CI replay (`make py-lint` / `make py-test` from
ship-pr failed-job tables) needs the same toolchain as CI: `pip install -r python/requirements-dev.txt`
for lint (including **Node** on PATH for pyright) and `pip install -r python/requirements-test.txt`
for tests.

Python parity tests require **bash** for shell helper comparisons. CI `python-tests` installs the required shell tooling;
local runs without it skip those cases via `pytest.mark.skipif`.

The live `/implement` path uses `python/cli.py ship pr`. `/report-tokens` is cut over to `python/cli.py report-tokens analyze`; the `run-analysis.sh` wrapper has been retired.

## Pre-push conflict handoff scope

`rebase.py` represents the bash exit-4 `ship_pr_pre_push` conflict handoff at
library level only. When the in-process conflict fixer waterfall exhausts on
remaining conflicts, it writes `ship-pr-rrr-after-phase14.flag` under the
resolved implement tmpdir and raises `PrePushConflictHandoff` with the conflict
files plus the `ship-pr-rrr-phase14` / `ship_pr_pre_push` tokens. Flag
write failures raise plain `Stalled` instead.

`python/ship.py` now persists the handoff state for the default path. The
`PrePushConflictHandoff` handler writes `RESUME_PHASE=ship-pr-rrr-phase14`,
`CALLER_KIND=ship_pr_pre_push`, and `CONFLICT_FILES` to `ship-pr-state.sh`, then
returns the normal stalled JSON/exit-4 contract. After the prompt-side
`skills/implement/references/conflict-resolution.md` Phase 1-4 procedure
succeeds, re-invoking the Python selector without `--resume-phase` sees
`ship-pr-rrr-after-phase14.flag`, re-enters `run_rebase_rebump` through
`rebase.rebase_and_push`, clears the flag plus resume tokens after a successful
force-push, and continues CI/merge processing. If the resume tokens exist but
the flag is absent, the Python path still returns
`needs_user_reason=unsupported-rebase-continuation` so stale or partial handoffs
fail closed. See `skills/implement/references/conflict-resolution.md` and issue
`#3404` for the cross-driver handoff contract.

## Phase 1 wiring outside `python/`

Plan acceptance lists four non-`python/` files (Makefile, CI workflow, docs, harnesses). The Python ship driver also maps `python-lint` / `python-tests` CI jobs to `make py-lint` / `make py-test`; keep that wiring with the ship path.

## Phase 4 scope note (branch hygiene)

The Phase 4 plan file list names `python/checks.py`, `python/test_checks.py`, and this README. The same branch may also carry ancillary harness or plugin surface updates (for example `scripts/test-lint-literal-counts.sh`, `scripts/test-plan-review-loop.sh`, `.claude-plugin/plugin.json`) that are not Phase-4 module ports; review those diffs separately from the `python/` parity work.

## Phase 6 scope note (`CI_FIX_REBASE_PENDING`)

`ci_monitor.py` deliberately omits the retired shell driver's `CI_FIX_REBASE_PENDING` pending-retry fast path: a verified-but-unpushed CI fix that fails `git push` terminates as `Outcome.STALLED` by design (stateless monitor, rebase limited to merge-conflict-only, shell driver retired). See issue #3405.

## Orphan flush-reset parity note

`finalize._local_cleanup` intentionally requires non-empty `git log` subject evidence before dropping local flush-only commits. Bash's empty-loop shape could reset with empty or malformed log output, but the Python port keeps the safer fail-closed behavior and pins it in `test_local_cleanup_does_not_reset_on_empty_orphan_evidence`.

## Migration status

Runtime logic is Python-first. Residual Bash is the explicit manifest inventory consumed by `python3 python/cli.py residual-bash paths`.

`python3 python/cli.py pr closes-issue` is the PR-body `Closes #N` recovery surface. Terminal shared Bash libraries and verified orphan includes are retired through `python/migrated-scripts.tsv`.
