# `scripts/lint-harness-pytest-partition.py`

## Purpose

Strict-partition guard for the multi-target pytest source files that #4439
sliced. For an explicit allow-list of files, it asserts that the
`test-harnesses` Makefile targets running that file partition it cleanly:
every test is collected by **exactly one** target — none left uncovered,
none counted twice. This locks in the per-target `-k` slicing (Tricks
A1/A2) and the research-target de-duplication (Trick A3) against
regression.

This sibling contract exists because `.claude/rules/script-md-siblings.md`
requires every script under `scripts/` to carry a neighboring
`<basename>.md`.

## Scope (and deliberate non-scope)

`ENFORCED` (top of the script) is the allow-list. It currently holds:

- `python/test_review_tally.py` — sliced into `findings_classification`,
  `tally_ and not emit`, `emit_tally`, `log_phase` (Trick A1).
- `python/test_review_pipeline.py` — seven pre-existing `-k` slices plus
  the orphan-4 slice narrowed onto `test-check-reviewer-failure-threshold`
  (Trick A2).
- `python/test_research.py` — a single full-file target
  (`test-render-findings-batch`) after the four redundant research targets
  were retired (Trick A3). A single full-file target is a valid partition;
  the guard fails if a duplicate full-file target is reintroduced.
- `python/test_agents.py`, `python/test_tokens.py`,
  `python/test_report_tokens_cost.py`, `python/test_timing.py`,
  `python/test_clarify.py` — the five previously-**untimed** full-file
  groups, now sliced into per-target `-k` selections (each target also
  wrapped with `timing harness-mark`). One target per file carries a
  `not (...)` catch-all so new tests stay covered.

The guard does **not** yet enforce the invariant globally. The remaining
timed-but-duplicated multi-target files (e.g. `test_run_logs.py`,
`test_implement_dispatch.py`, `test_release.py`) still run their full file
under several target names; de-duplicating those is a tracked follow-up. To
bring a file under the guard, slice its targets into disjoint `-k`/node-id
selections first, then add the file to `ENFORCED`.

## Invariants

- For each `ENFORCED` file: `union(selections) == full-file collection` and
  no node-id appears in more than one target's selection.
- A `FULL-FILE` selection (no `-k`, no node-ids) collects the whole file;
  two such targets for one file overlap fully and fail the guard.
- Parsing mirrors `scripts/test-harness-shards-coverage.sh`: the same
  `CARVE_OUTS` set is excluded, and `test-harnesses` / `test-harnesses-N`
  aggregate rules are ignored.

## Primary Callers / Makefile Wiring

Invoked from `scripts/test-harness-shards-coverage.sh`'s non-`--self-test`
`main()` path, so it rides the `test-harness-shards-coverage` harness
target (shard-bound and a `make lint` prerequisite via `test-harnesses`).
No standalone Makefile target. Run it directly with
`python3 scripts/lint-harness-pytest-partition.py` (exit 0 = clean
partition; exit 1 = violation, with a per-file diff on stderr).

## Runtime Requirement

Runs `python3 -m pytest --co` per selection, so pytest and the test
dependencies must be on PATH. That holds on the `test-harnesses` shard that
owns `test-harness-shards-coverage`; the guard fails loudly (collected 0
tests) rather than passing silently if collection cannot run.

## Edit-in-Sync

- Update `ENFORCED` when slicing a new file or retiring a target that
  changes an enforced file's target set.
- Keep `CARVE` in sync with `CARVE_OUTS` in
  `scripts/test-harness-shards-coverage.sh`.
- This guard is covered by the `test-harness-shards-coverage` harness run
  (it executes against the real `Makefile` there); there is no separate
  `test-*` harness for it.
