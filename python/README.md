# larch Python runtime

Mostly-flat `python/` tree for larch's remaining stdlib-only runtime modules. The shared leaf layer lives in the `larch/` package: `larch.io`, `larch.errors`, `larch.outcomes`, and the `larch.core` home for the most-depended-on leaf utilities (`proc`, `config`, `logging_util`, `redact`, `retry`, `run_context`). `/implement` Step 8+ and `/report-tokens` are Rust-owned through `scripts/larch.sh`. Python 3.11 remains required for the separately owned merge and finalization commands that the Rust ship lifecycle composes. Linters and pytest are dev/CI-only and are never imported by runtime code.

## Layout

- `larch/` — foundation package for the stdlib-only shared leaf layer; domain modules move in under later packaging children
- `larch/core/config.py` — tunables (exit codes, timeouts, tier order, env-var names)
- `larch/core/proc.py` — injectable subprocess seam
- `larch/errors.py`, `larch/outcomes.py`, `larch/core/run_context.py` — typed errors and run context
- `larch/io.py` — shared text, `KEY=value`, and atomic-write helpers for larch wire files
- `larch/core/logging_util.py` — breadcrumbs + JSONL journal for surviving Python commands
- `larch/core/redact.py`, `larch/core/retry.py` — secret redaction and transient retry helpers
- The Rust `larch lint gitleaks` command owns checksum-pinned scanner bootstrap for local pre-commit. CI uses its separately verified workflow installer so the dedicated scanner gate does not build `larch-cli`.
- `rendering.py` — prompt renderers, Mermaid sanitizer, diagrams upserter, and generated-artifact generators now exposed through `python/cli.py` (`render`, `mermaid`, `diagrams`, and `generate` domains).
- `voting.py` — voting, tally, parse-rate, ballot parsing, scoreboard, and focus-area enum CLI surfaces.
- `git.py`, `gh.py`, `agents.py` — typed `git` / `gh` / fixer launcher surfaces
- `report_tokens_models.py`, `report_tokens_scan.py`, `report_tokens_cost.py` — bounded helpers for remaining Python token analytics and the `render run-summary` compatibility payload. Token measurements are Rust-owned after #8508, and Rust owns `token report`, `token cost`, and `token render-cost-line` after #8507; these helpers do not own `/report-tokens` or `final-report`, whose Python entrypoints retired in #8088 and #8090.
- `larch/git/rebase.py` — compatibility rebase decisions used by surviving Python workflows; the Step 8 ship lifecycle does not call it.
- Checks selection, fixer evidence, lint-fix dispatch, and the bounded repair
  loop are Rust-owned. Their Python runtime modules retired at the #8627 atomic
  cutover; production callers enter through `scripts/larch.sh checks ...`.
- `ci_monitor.py` — retained for surviving Python merge and CI callers. The Rust-owned `/implement` Step 8 and `/complete-umbrella` leaf ship paths use the Rust `ci` commands directly.
- **Phase 5 compatibility layer**: `run_logs.py` is a typed Rust-command facade,
  `run_log_batch.py` is a parity mirror for bounded compatibility callers and the historical reader,
  and `run_log_manifest.py` is read-only. `tracking_issue.py` contains only pure
  PR-footer helpers; its lifecycle, sentinel, and GitHub behavior is Rust-owned behind
  typed `rust_runtime.py` calls through `scripts/larch.sh`. `tokens.py`,
  `pr_body.py`, `push.py`, `pr.py`, and `merge.py` are retained PR/merge/logging components with session-local
  implement staging through the Rust-owned run-log refresh, complete terminal snapshot and archive publication from
  Step 18, and log-free cleanup from Step 19. After #8789, Rust owns
  `pr compose-summary`, `tracking post-issue`, and the reusable PR-body redaction
  helper. `pr_body.py` retains the Python PR-body/redaction bridge through the
  remaining `pr` command cutover, plus `render run-summary` and `diagram code-flow`. `merge.py`
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
  `progress`, and ship result-env commands. It keeps established Python result
  and error contracts without staging an artifact.
- `larch/complete_umbrella.py` owns the one-call `/complete-umbrella` Step 0
  composition. It validates and combines Rust lifecycle, repository, resume,
  session, parent-start, Write-hook, and model envelopes while keeping every
  Rust command behind `scripts/larch.sh`.
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

The live `/implement` path uses `scripts/larch.sh ship pr`. Rust owns the lifecycle, initial ship-state seeding, and result-env persistence. The retired Python command has no CLI registration or production fallback. `/report-tokens` is likewise cut over to `scripts/larch.sh report-tokens analyze`; the `run-analysis.sh` wrapper has been retired.

## Pre-push conflict handoff scope

The Rust ship lifecycle persists `RESUME_PHASE=ship-pr-rrr-phase14`,
`CALLER_KIND=ship_pr_pre_push`, and `CONFLICT_FILES` when a pre-push rebase
requires the prompt-side conflict resolver. After
`skills/implement/references/conflict-resolution.md` completes the rebase,
re-invoking the Step 8 wrapper resumes from durable state, clears the flag and
handoff keys only after a successful lease-protected push, and continues CI and
merge processing. Invalid or partial continuation tokens fail closed with
`needs_user_reason=unsupported-rebase-continuation`.

## Phase 1 wiring outside `python/`

Plan acceptance lists four non-`python/` files (Makefile, CI workflow, docs, harnesses). Rust CI classification preserves the `python-pyright` and `python-tests` job identities; keep their `make py-typecheck` and `make py-test` wiring.

## Phase 4 scope note (branch hygiene)

The Phase 4 plan file list names `python/checks.py`, `python/test_checks.py`, and this README. The same branch may also carry ancillary harness or plugin surface updates (for example `make test-plan-review-loop`, `.claude-plugin/plugin.json`) that are not Phase-4 module ports; review those diffs separately from the `python/` parity work.

## Phase 6 scope note (`CI_FIX_REBASE_PENDING`)

`ci_monitor.py` deliberately omits the retired shell driver's `CI_FIX_REBASE_PENDING` pending-retry fast path: a verified-but-unpushed CI fix that fails `git push` terminates as `Outcome.STALLED` by design (stateless monitor, rebase limited to merge-conflict-only, shell driver retired). See issue #3405.

## Migration status

Runtime logic is Python-first where its command owner remains Python. Residual Bash is the explicit manifest inventory consumed by `scripts/larch.sh residual-bash paths`.

`python3 python/cli.py pr closes-issue` is the PR-body `Closes #N` recovery surface. Terminal shared Bash libraries and verified orphan includes are retired through `python/migrated-scripts.tsv`.

## Bgjob runtime package

`bgjob {adapt,start,wait,status,reap}` is Rust-owned; invoke it through `scripts/larch.sh`. `python/larch/bgjob/` retains only the shared record, path-validation, and registry-reading helpers that other Python runtime modules still import.
