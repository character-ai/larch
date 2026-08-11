# larch Python runtime

Mostly-flat `python/` tree for larch's stdlib-only runtime modules (Python ≥ 3.11 for the `/implement` Step 8+ ship driver). The shared leaf layer lives in the `larch/` package: `larch.io`, `larch.errors`, `larch.outcomes`, and the `larch.core` home for the most-depended-on leaf utilities (`proc`, `config`, `logging_util`, `redact`, `retry`, `run_context`). `/implement` Step 8+ uses `python/cli.py ship pr` (delegating to `python/ship.py`). `/report-tokens` is Rust-owned via `scripts/larch.sh report-tokens analyze`. Linters and pytest are dev/CI-only and are never imported by runtime code.

## Layout

- `larch/` — foundation package for the stdlib-only shared leaf layer; domain modules move in under later packaging children
- `larch/core/config.py` — tunables (exit codes, timeouts, tier order, env-var names)
- `larch/core/proc.py` — injectable subprocess seam
- `larch/errors.py`, `larch/outcomes.py`, `larch/core/run_context.py` — typed errors and run context
- `larch/io.py` — shared text, `KEY=value`, and atomic-write helpers for larch wire files
- `larch/core/logging_util.py` — breadcrumbs + JSONL journal (observability only); `quiet_init()` owns Python stream routing, and `contract_stream()` sends ship-driver JSON to fd 3 after self-initialized quiet
- `larch/core/redact.py`, `larch/core/retry.py` — secret redaction and transient retry helpers
- The Rust `larch lint gitleaks` command owns checksum-pinned scanner bootstrap for local pre-commit. CI uses its separately verified workflow installer so the dedicated scanner gate does not build `larch-cli`.
- `rendering.py` — prompt renderers, Mermaid sanitizer, diagrams upserter, and generated-artifact generators now exposed through `python/cli.py` (`render`, `mermaid`, `diagrams`, and `generate` domains).
- `voting.py` — voting, tally, parse-rate, ballot parsing, scoreboard, and focus-area enum CLI surfaces.
- `git.py`, `gh.py`, `agents.py` — typed `git` / `gh` / fixer launcher surfaces
- `report_tokens_models.py`, `report_tokens_scan.py`, `report_tokens_cost.py` — bounded helpers for the still-Python `token` and analytics surfaces, plus the `render run-summary` compatibility payload. Their later command owners are #7680 and #7684; they do not own `/report-tokens` or `final-report`, both of which retired their Python entrypoints in #8088 and #8090.
- `rebase.py` — CI-fix rebase decision and verification surfaces used by the default Python ship driver.
- `checks.py` — local relevant-checks runner and lint-fix loop (Phase 4); local
  fixer dispatch does **not** call `agents.classify_launch_failure` (bash #3207 parity)
- `ci_monitor.py` — live on the default Python Step 8+ path; `python/ship.py` calls it from
  the merge loop after PR creation to poll CI, classify failures, collect failed-job data,
  run the fixer waterfall, and return the GOTO-Rebase signal.
- `larch/implement/complete_umbrella_ship.py` — standalone leaf prepare and ship driver for `/complete-umbrella`. It reuses typed Git, GitHub, CI, redaction, retry, and issue-mutation owners without fabricating the `IMPLEMENT_TMPDIR` state required by `ship pr`. It persists a leaf-bound no-follow state file, waits five minutes between CI reads, emits a bounded failure digest, admin-merges green PRs, and verifies issue, branch, and synchronized-main postconditions.
- **Phase 5** (live via default Python ship driver): `run_logs.py` is a typed Rust-command facade,
  `run_log_batch.py` is a parity mirror for bounded compatibility callers and the historical reader,
  and `run_log_manifest.py` is read-only. `tracking_issue.py` contains only pure
  PR-footer helpers; its lifecycle, sentinel, and GitHub behavior is Rust-owned behind
  typed `rust_runtime.py` calls through `scripts/larch.sh`. `tokens.py`,
  `pr_body.py`, `push.py`, `pr.py`, and `merge.py` are PR/merge/logging ports with session-local
  implement staging through the Rust-owned run-log refresh, complete terminal snapshot and archive publication from
  Step 18, and log-free cleanup from Step 19. `merge.py`
  classifies the eight `python/cli.py merge pr` `MERGE_RESULT` literals; driver-only `already_merged` is
  documented in `config.MERGE_RESULT_DRIVER_ALREADY_MERGED` for `refresh_logs_checkpoint` skip parity.
  Tool-failure batch capture remains deferred to Phase 7 wiring; bash launchers still own
  `append-tool-failure.sh` calls on the live path.
- `larch/issue/file_oos.py` is not a production OOS command owner. Its retained
  in-process parsing, normalization, and compatibility helpers are assigned to
  #7680; the #7681 Step 8 workflow consumes its run-id resolver for bookkeeping.
  All six OOS commands migrated by #8178 and #8179 enter through
  `scripts/larch.sh` and are Rust-owned.
- `larch/report/run_log_archive.py`, `run_lifecycle.py`, `storage_config.py`,
  and `run_log_publish.py` retain bounded Python compatibility readers, types,
  and Rust-command facades. Rust
  owns archive creation, materialization, standalone and lifecycle publication,
  synchronization, tool-first layout migration, historical repair sweeps, and
  completed-implement-run cleanup. None of these Python modules replaces a
  Rust-owned run-log command.
- `larch/core/rust_runtime.py` is the typed ship-facing facade for Rust
  `run-log refresh`, `tracking-issue`, `execution-issues`, `final-report write`,
  and `progress` commands. It keeps established Python result and error
  contracts without staging an artifact.
- `larch/report/object_store.py` remains a compatibility/test provider adapter;
  it has no production run-log command caller.
- `tests/`: unit tests mirror package layout under `python/tests/`.
- `test_support.py`: shared list-queue `RecordingRunner` used by tests such as `test_run_logs.py` and `test_ci_monitor.py`.

## Dependencies

| File | Purpose |
|------|---------|
| `requirements-dev.txt` | Ruff, Pyright, and Pytest (`make py-lint` and development tests) |
| `requirements-test.txt` | pytest only (Python Tests CI / `make py-test`; no Node) |

## Run locally

From the repository root (after `pip install -r python/requirements-dev.txt` and/or
`python/requirements-test.txt`):

```bash
make py-lint   # cd python && ruff check . && pyright
make py-test   # cd python && pytest
```

`make lint` does not invoke `py-lint` or `py-test`; use those targets explicitly. CI runs
Ruff in `lint-local`, Pyright in `python-pyright`, and tests in `python-tests`. Install
`python/requirements-dev.txt` for linting (including **Node** on PATH for Pyright) and
`python/requirements-test.txt` for tests.

Python parity tests require **bash** for shell helper comparisons. CI `python-tests` installs the required shell tooling;
local runs without it skip those cases via `pytest.mark.skipif`.

The live `/implement` path uses `python/cli.py ship pr`. `/report-tokens` is cut over to `scripts/larch.sh report-tokens analyze`; the `run-analysis.sh` wrapper has been retired.

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

Plan acceptance lists four non-`python/` files (Makefile, CI workflow, docs, harnesses). The Python ship driver maps `python-pyright` and `python-tests` CI jobs to `make py-typecheck` and `make py-test`; keep that wiring with the ship path.

## Phase 4 scope note (branch hygiene)

The Phase 4 plan file list names `python/checks.py`, `python/test_checks.py`, and this README. The same branch may also carry ancillary harness or plugin surface updates (for example `make test-plan-review-loop`, `.claude-plugin/plugin.json`) that are not Phase-4 module ports; review those diffs separately from the `python/` parity work.

## Phase 6 scope note (`CI_FIX_REBASE_PENDING`)

`ci_monitor.py` deliberately omits the retired shell driver's `CI_FIX_REBASE_PENDING` pending-retry fast path: a verified-but-unpushed CI fix that fails `git push` terminates as `Outcome.STALLED` by design (stateless monitor, rebase limited to merge-conflict-only, shell driver retired). See issue #3405.

## Migration status

Runtime logic is Python-first where its command owner remains Python. Residual Bash is the explicit manifest inventory consumed by `scripts/larch.sh residual-bash paths`.

`python3 python/cli.py pr closes-issue` is the PR-body `Closes #N` recovery surface. Terminal shared Bash libraries and verified orphan includes are retired through `python/migrated-scripts.tsv`.

## Bgjob runtime package

`bgjob {adapt,start,wait,status,reap}` is Rust-owned; invoke it through `scripts/larch.sh`. `python/larch/bgjob/` retains only the shared record, path-validation, and registry-reading helpers that other Python runtime modules still import.
