# larch Python runtime

Mostly-flat `python/` tree for larch's remaining stdlib-only runtime modules. The shared leaf layer lives in the `larch/` package: `larch.io`, `larch.errors`, `larch.outcomes`, and the `larch.core` home for the most-depended-on leaf utilities (`proc`, `config`, `logging_util`, `redact`, `retry`, `run_context`). `/implement` Step 8+, pull-request merge processing, and `/report-tokens` are Rust-owned through `scripts/larch.sh`. Python 3.11 remains required for surviving finalization commands. Linters and pytest are dev/CI-only and are never imported by runtime code.

## Layout

- `larch/` — foundation package for the stdlib-only shared leaf layer; domain modules move in under later packaging children
- `larch/core/config.py` — tunables (exit codes, timeouts, tier order, env-var names)
- `larch/core/proc.py` — injectable subprocess seam
- `larch/errors.py`, `larch/outcomes.py`, `larch/core/run_context.py` — typed errors and run context
- `larch/io.py` — shared text, `KEY=value`, and atomic-write helpers for larch wire files
- `larch/core/logging_util.py` — breadcrumbs + JSONL journal for surviving Python commands
- `larch/core/redact.py`, `larch/core/retry.py`: in-process secret redaction and transient retry helpers. The four public `redact` commands are Rust-owned through `scripts/larch.sh`; this module is not their fallback.
- The Rust `larch lint gitleaks` command owns checksum-pinned scanner bootstrap for local pre-commit. CI uses its separately verified workflow installer so the dedicated scanner gate does not build `larch-cli`.
- `larch/rendering/rendering.py` - the remaining voter and scope-anchor prompt renderers exposed through `python/cli.py render`. Rust owns `render plan-review`, `mermaid sanitize`, and `diagrams upsert` through `scripts/larch.sh`.
- `voting.py` — voting, tally, parse-rate, ballot parsing, scoreboard, and focus-area enum CLI surfaces.
- `gh.py`, `pr_body.py`, `agents.py` — typed `gh` / PR-body / fixer launcher surfaces. `larch.git.git`, `larch.git.rebase`, and `larch.core.coder_delta_guards` retired in #8880 (Rust owns ship rebase; a frozen `git_frozen.py` remains for finalize parity only).
- `report_tokens_models.py`, `report_tokens_scan.py`, `report_tokens_cost.py` — bounded helpers for remaining Python token analytics and the `render run-summary` compatibility payload. Token measurements are Rust-owned after #8508; Rust owns `token report`, `token cost`, and `token render-cost-line` after #8507 and the token-budget and PR line-count commands after #8797. These helpers do not own those commands, `/report-tokens`, or `final-report`, whose Python entrypoints retired in #8088 and #8090.
- Checks selection, fixer evidence, lint-fix dispatch, and the bounded repair
  loop are Rust-owned. Their Python runtime modules retired at the #8627 atomic
  cutover; production callers enter through `scripts/larch.sh checks ...`.
- **Phase 5 compatibility layer**: `run_logs.py` is a typed Rust-command facade,
  `run_log_batch.py` is a parity mirror for bounded compatibility callers and the historical reader,
  and `run_log_manifest.py` is read-only. `tracking_issue.py` contains only pure
  PR-footer helpers; its lifecycle, sentinel, and GitHub behavior is Rust-owned behind
  typed `rust_runtime.py` calls through `scripts/larch.sh`. `tokens.py`,
  `pr_body.py`, `push.py`, and `pr.py` are retained PR/logging components with session-local
  implement staging through the Rust-owned run-log refresh, complete terminal snapshot and archive publication from
  Step 18, and log-free cleanup from Step 19. After #8797, `tokens.py` retains
  only Python token-analysis and compatibility helpers; the budget and PR
  line-count commands have no Python registration or fallback. After #8789,
  Rust owns
  `pr compose-summary`, `tracking post-issue`, and the reusable PR-body redaction
  helper. `pr_body.py` retains the Python PR-body/redaction bridge through the
  remaining `pr` command cutover, plus `render run-summary` and `diagram code-flow`.
  Rust `merge pr` classifies the established `MERGE_RESULT` literals; driver-only `already_merged` is
  documented in `config.MERGE_RESULT_DRIVER_ALREADY_MERGED` for `refresh_logs_checkpoint` skip parity.
  Tool-failure batch capture remains deferred to Phase 7 wiring; bash launchers still own
  `append-tool-failure.sh` calls on the live path.
- `larch/issue/issue_wire.py` retains the untrusted-content helpers used by the
  #7686 Python `render voter` consumer. All OOS commands and helpers are
  Rust-owned; their retired Python references live only under `fixtures/`.
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
- `larch/report/object_store.py` remains a compatibility/test provider adapter;
  it has no production run-log command caller.
- `tests/`: unit tests mirror package layout under `python/tests/`.
- `test_support.py`: shared list-queue `RecordingRunner` used by tests such as `test_run_logs.py`.

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

## Migration status

Runtime logic is Python-first where its command owner remains Python. Residual Bash is the explicit manifest inventory consumed by `scripts/larch.sh residual-bash paths`.

`scripts/larch.sh pr closes-issue` is the Rust-owned PR-body `Closes #N` recovery surface. Terminal shared Bash libraries and verified orphan includes are retired through `python/migrated-scripts.tsv`.

## Bgjob runtime package

`bgjob {adapt,start,wait,status,reap}` is Rust-owned; invoke it through `scripts/larch.sh`. `python/larch/bgjob/` retains only the shared record, path-validation, and registry-reading helpers that other Python runtime modules still import.
