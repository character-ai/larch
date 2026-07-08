## Goal
Implement issue #6540: [IMPLEMENTING] bgjob migration wrap-up: shared docs, final-summary sources, allowlist end state (#6524 chunk 11/11).

## Implementation Plan
## Plan

## Context

Parent: #6524 "Migrate remaining run_in_background call sites to bgjob start/wait (part 2)" — chunk 11/11 (wrap-up).

Scope: shared-doc and lint end-state — bgjob NEVER rules in `orchestrator-never.md`, final-summary source rebinds in `final-summary-emit.md` and its harness, workflow/run-log/linting documentation, and verification that the bg-wait allowlist reached its end state.

Dependencies: blocked by #6534 (chunk 5/11: /design wrap-up), #6538 (chunk 9/11: stall/state classifiers), and #6539 (chunk 10/11: /research lanes). Merge those first — this chunk documents and pins the fully migrated state (the remaining chunks are transitive prerequisites through those three).

The parent's vetted plan was split into 11 self-contained chunk issues because a single /implement run could not complete all ~74 firm files. Nothing from the parent's failed run merged; implement this chunk from scratch on current main. Do not modify files outside this chunk's scope headings.

## Approach (global invariants inherited from #6524)

1. Keep `skills/shared/bgjob-wait.md` as the normative wait contract.
2. Bgjob result envs are completion truth for long-running steps; terminal sentinels remain as transition compatibility markers.
3. Gate continuation on `BGJOB_RC=0` plus required KVs (Step 8 ship driver excluded from that gate — handoff sidecars are authoritative for `ship route-exit`).
4. Keep legacy hooks and marker helpers functional but inert until #6516 deletes them; do not delete #6516-owned defense text unless it conflicts with migrated call sites.

## Files to modify/create

### UPDATED: skills/shared/orchestrator-never.md
- Add bgjob wait NEVER rules.
- Narrow retained task-notification rules to compatibility-only docs.
- Add Step 8 carve-out: do not treat numeric driver rc in handoff sidecars as generic bgjob failure.
- Do not delete #6516-owned defense text unless it conflicts with migrated call sites.

### UPDATED: skills/shared/final-summary-emit.md
- Rebind `/design` final-summary sources to captured bgjob `DONE` stdout and result env reads.
- Rebind `/implement` Step 17 and Step 18b from task-notification sources to final `bgjob wait` stdout with `BGJOB_RC=0` gate (Step 8 ship driver excluded from that gate).

### UPDATED: scripts/test-render-cost-line-callsites.sh
- Update final-summary source assertions away from task-notification stdout.

### UPDATED: docs/workflow-lifecycle.md
- Document bgjob result envs as completion truth for long-running steps.
- Document diagnostics in bgjob logs and result envs.
- Document merge-env truncation before each start.
- Document Step 8 handoff-sidecar carve-out and per-lane unique step slugs.

### UPDATED: docs/run-logs.md
- Extend bgjob diagnostics and result env documentation before run-log capture.

### UPDATED: docs/linting.md
- Update bg-wait coverage and writer-parity docs.
- Add `scripts/test-bgjob.sh` shard expectations.

### MAY_UPDATE: python/larch/lint/bg_wait_allowlist.txt
- End-state verification: after the sibling chunks, the allowlist must hold at most the `skills/shared/orchestrator-never.md` compatibility row. Remove any leftover migrated-file rows a sibling chunk missed; otherwise leave the file untouched.

## Edge cases

- `orchestrator-never.md` remains on the allowlist by design — it is the single retained compatibility entry until #6516.
- Task-notification defense text that still guards unmigrated third-party surfaces stays; only rules that conflict with migrated larch call sites are narrowed.
- `final-summary-emit.md` rebinds must keep the Step 8 ship-driver exclusion from the `BGJOB_RC=0` gate.

## Failure modes

- Docs claim bgjob completion truth for a surface an earlier chunk did not actually migrate (verify against the merged tree, not this plan).
- Over-pruned NEVER rules delete #6516 compatibility coverage.
- `test-render-cost-line-callsites.sh` still pins task-notification literals and fails CI after the rebind.
- Allowlist end state asserted while a leftover row remains.

## Testing strategy

1. `bash scripts/test-render-cost-line-callsites.sh`
2. `python3 python/cli.py lint bg-wait-coverage`
3. `python3 python/cli.py lint bg-wait-writer-parity`
4. End-state verification: `git grep -l "run_in_background" skills/` returns only lint-allowlisted files and historical run logs; `python/larch/lint/bg_wait_allowlist.txt` holds at most the `skills/shared/orchestrator-never.md` compatibility entry.
5. Final validation: `make py-lint`, `make py-test`, affected `test-harnesses-N` shards.

## Implementation notes

- This chunk is documentation, shared prose, and pins only; no wrapper or Python behavior changes.
- Keep changed prompt literals covered by prompt-shape harnesses.
- Do not retire legacy hooks, defense docs, or `python/larch/implement/bg_wait.py`; #6516 owns deletion.

## Acceptance

1. `git grep -l "run_in_background" skills/` returns only lint-allowlisted files and historical run logs; `python/larch/lint/bg_wait_allowlist.txt` holds at most the `skills/shared/orchestrator-never.md` compatibility entry; `python3 python/cli.py lint bg-wait-coverage` enforces this in `make lint`.
2. `orchestrator-never.md` carries bgjob wait NEVER rules, the Step 8 handoff-sidecar carve-out, and compatibility-only task-notification rules.
3. `/design` and `/implement` final-summary sources are rebound to captured bgjob `DONE` stdout and result env reads (Step 8 ship driver excluded from the `BGJOB_RC=0` gate), asserted by `scripts/test-render-cost-line-callsites.sh`.
4. `docs/workflow-lifecycle.md`, `docs/run-logs.md`, and `docs/linting.md` document bgjob completion truth, diagnostics, merge-env truncation, the Step 8 carve-out, per-lane slugs, and the `scripts/test-bgjob.sh` shard.
5. `make py-lint`, `make py-test`, and all affected `test-harnesses` shards pass.
6. Post-merge validation for the whole series: one full `/design` run and one full `/implement --merge` run on a MODERATE issue complete with zero `<task-notification>` entries for migrated larch launches; #6516 stays blocked until all chunk issues of #6524 hold their criteria.

diff_added: 140
diff_deleted: 90
mechanical_churn: true
diff_lines: 230

## Test plan
(no test plan section in plan-file)
