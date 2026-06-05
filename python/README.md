# larch Python runtime

Flat `python/` tree for larch's stdlib-only runtime modules (Python ≥ 3.11). Most modules still support the `scripts/ship-pr.sh` → Python cutover work, but `/report-tokens` is live now through `report_tokens_cli.py` and the `skills/report-tokens/scripts/run-analysis.sh` wrapper. Linters and pytest are dev/CI-only and are never imported by runtime code.

## Layout

- `config.py` — tunables (exit codes, timeouts, tier order, env-var names)
- `proc.py` — injectable subprocess seam
- `errors.py`, `outcomes.py`, `run_context.py` — typed errors and run context
- `logging_util.py` — breadcrumbs + JSONL journal (observability only); `quiet_init()` mirrors `scripts/lib-quiet.sh`, and `contract_stream()` sends ship-driver JSON to fd 3 after self-initialized quiet
- `redact.py`, `retry.py` — ports of `redact-secrets.sh` / `lib-net.sh`
- `git.py`, `gh.py`, `agents.py` — typed `git` / `gh` / fixer launcher surfaces
- `version_bump.py` — shared semver classification helpers used by release preparation and Python parity tests.
- `report_tokens_models.py`, `report_tokens_scan.py`, `report_tokens_cost.py`, `report_tokens_render.py`, `report_tokens_plot.py`, `report_tokens_issue.py`, `report_tokens_cli.py` — live `/report-tokens` scan, pricing, render, plot-subprocess, issue-posting, and CLI pipeline.
- `rebase.py` — Phase 3 port for CI-fix rebase decision and verification surfaces; dev/CI-only until Phase 7.
- `checks.py` — local relevant-checks runner and lint-fix loop (Phase 4); local
  fixer dispatch does **not** call `agents.classify_launch_failure` (bash #3207 parity)
- `ci_monitor.py` — Phase 6 CI poll + classify + collect + fixer-waterfall + GOTO-Rebase signal
  (not wired into the live `/implement` path until Phase 7)
- **Phase 5** (dev/CI-only until Phase 7): `run_logs.py`, `tokens.py`, `tracking_issue.py`,
  `pr_body.py`, `push.py`, `pr.py`, `oos.py`, `merge.py` — PR/merge/logging ports with split
  `flush_logs_pre` (may commit log batches) vs `flush_logs_post` (tmpdir-only). `merge.py`
  classifies the eight `merge-pr.sh` `MERGE_RESULT` literals; driver-only `already_merged` is
  documented in `config.MERGE_RESULT_DRIVER_ALREADY_MERGED` for `flush_logs_pre` skip parity.
  Tool-failure batch capture remains deferred to Phase 7 wiring; bash launchers still own
  `append-tool-failure.sh` calls on the live path.
- `test_<module>.py` — colocated unit tests; `test_support.py` provides the shared list-queue `RecordingRunner` (with `test_run_logs.py` preserving `git_commits` via a subclass and `test_ci_monitor.py` retaining its keyed runner); `test_checks_bash_parity.py` bash-sourced parity harness; `test_stdlib_only.py` enforces stdlib-only imports

## Dependencies

| File | Purpose |
|------|---------|
| `requirements-dev.txt` | ruff, pylint, pyright (Python Lint CI / `make py-lint`) |
| `requirements-test.txt` | pytest only (Python Tests CI / `make py-test`; no Node) |

## Run locally

From the repository root (after `pip install -r python/requirements-dev.txt` and/or
`python/requirements-test.txt`):

```bash
make py-lint   # cd python && ruff check . && pylint . && pyright
make py-test   # cd python && pytest
```

`make lint` does not invoke `py-lint` or `py-test`; use those targets explicitly or rely on
CI `python-lint` / `python-tests` jobs. Per-job CI replay (`make py-lint` / `make py-test` from
ship-pr failed-job tables) needs the same toolchain as CI: `pip install -r python/requirements-dev.txt`
for lint (including **Node** on PATH for pyright) and `pip install -r python/requirements-test.txt`
for tests.

Python parity tests require **bash** for shell helper comparisons. CI `python-tests` installs the required shell tooling;
local runs without it skip those cases via `pytest.mark.skipif`.

The live `/implement` path still uses bash until Phase 7 (`LARCH_SHIP_PR_IMPL=python`). `/report-tokens` is already cut over to Python; only the shell wrapper remains for skill compatibility and quiet-mode stream setup.

## Pre-push conflict handoff scope

`rebase.py` represents the bash exit-4 `ship_pr_pre_push` conflict handoff at
library level only. When the in-process conflict fixer waterfall exhausts on
non-bump-only conflicts, it writes `ship-pr-rrr-after-phase14.flag` under the
resolved implement tmpdir and raises `PrePushConflictHandoff` with the conflict
files plus the `ship-pr-rrr-phase14` / `ship_pr_pre_push` tokens. Bump-only or
mixed conflicts, conflicts that remain after a tier reported success, and flag
write failures all raise plain `Stalled` instead.

Phase 7 driver wiring remains deferred: no Python path currently emits exit 4,
writes `RESUME_PHASE` / `CALLER_KIND` state, emits `CONFLICT_FILES`, or parses
`--resume-phase ship-pr-rrr-phase14`.

## Phase 1 wiring outside `python/`

Plan acceptance lists four non-`python/` files (Makefile, CI workflow, docs, harnesses). **`scripts/ship-pr.sh`** is an intentional fifth wiring change: failed-job replay maps `python-lint` / `python-tests` CI jobs to `make py-lint` / `make py-test` (see `scripts/test-ship-pr.sh` replay cases). Revert only if replay stays allowlist-only until a later phase.

## Phase 4 scope note (branch hygiene)

The Phase 4 plan file list names `python/checks.py`, `python/test_checks.py`, and this README. The same branch may also carry ancillary harness or plugin surface updates (for example `scripts/test-lint-literal-counts.sh`, `scripts/test-plan-review-loop.sh`, `.claude-plugin/plugin.json`) that are not Phase-4 module ports; review those diffs separately from the `python/` parity work.

## Phase 6 scope note (`CI_FIX_REBASE_PENDING`)

`ci_monitor.py` deliberately omits bash ship-pr's `CI_FIX_REBASE_PENDING` pending-retry fast path: a verified-but-unpushed CI fix that fails `git push` terminates as `Outcome.STALLED` by design (stateless monitor, rebase limited to merge-conflict-only, bash retired — not a parity gap). See issue #3405.
