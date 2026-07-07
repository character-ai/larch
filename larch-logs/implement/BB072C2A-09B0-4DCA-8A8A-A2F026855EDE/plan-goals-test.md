## Goal
Implement issue #6539: [IMPLEMENTING] Migrate /research and validation lanes to per-lane bgjob slugs (#6524 chunk 10/11).

## Implementation Plan
## Plan

## Context

Parent: #6524 "Migrate remaining run_in_background call sites to bgjob start/wait (part 2)" — chunk 10/11.

Scope: migrate the /research research and validation external lanes from `run_in_background` to per-lane bgjob start/wait with unique `--step` slugs, and update the research structure harness.

Dependencies: blocked by #6530 (chunk 1/11: bgjob-wait contract, which documents per-lane unique slugs and merge-env truncation). Merge it first. Independent of the /design and /implement chunks — can proceed in parallel with them.

The parent's vetted plan was split into 11 self-contained chunk issues because a single /implement run could not complete all ~74 firm files. Nothing from the parent's failed run merged; implement this chunk from scratch on current main. Do not modify files outside this chunk's scope headings; sibling chunk issues own them.

## Approach (global invariants inherited from #6524)

1. Keep `skills/shared/bgjob-wait.md` as the normative wait contract.
2. Make each migrated lane launch a foreground launcher that prints only:
   `BGJOB_STATUS=STARTED STEP=<name> PGID=<n>`
3. **Clear or recreate each per-lane merge-result env before `bgjob start`.**
4. Treat `$TMPDIR/bgjob/<step>.result.env` as the completion source of truth after `bgjob wait` returns `DONE`.
5. Gate normal continuation on both `BGJOB_RC=0` and required lane KVs present in the final `DONE` stdout and/or the bgjob result env.
6. Treat `DEAD`, `BGJOB_RC=timeout`, `BGJOB_RC=orphaned`, or missing KVs as the lane's existing failure branch. **Never treat `bgjob wait` shell exit 0, `DONE` alone, start-launcher stdout, or notification-time wrapper stdout as sufficient for continuation.**
7. **Parallel lanes:** assign a unique `--step` slug per concurrent external lane so registry rows and result envs cannot clobber each other; never reuse a slug across concurrent external reviewers.
8. Keep legacy hooks and marker helpers functional but inert until #6516 deletes them.

## Files to modify/create

### UPDATED: skills/research/references/research-phase.md
- Replace Codex lane `run_in_background` instructions with per-lane bgjob start and wait.
- Keep Claude Agent fallback unchanged.
- For parallel lanes, start each separately with a **unique `--step` slug** (`research-arch`, `research-edge`, `research-ext`, `research-sec`) and wait each separately.
- Truncate per-lane merge-result envs before start.

### UPDATED: skills/research/references/validation-phase.md
- Apply the same bgjob conversion to Cursor and Codex validation lanes.
- Require unique `--step` slugs per lane (`validation-code`, `validation-cursor`, `validation-codex`).

### UPDATED: scripts/test-research-structure.sh
- Assert research and validation lanes use bgjob, not `run_in_background`.
- Assert unique per-lane `--step` slugs (`research-arch`, `research-edge`, `validation-cursor`, etc.).
- Add collision regression: parallel lane starts must not overwrite distinct result env paths.

### UPDATED: python/larch/lint/bg_wait_allowlist.txt
- Chunk-scoped: remove the `skills/research/references/research-phase.md` and `skills/research/references/validation-phase.md` rows (their prose is migrated by this chunk).
- Keep every other row; sibling chunks own them.

## Edge cases

- Parallel research and validation lanes must use distinct `--step` slugs so registry rows and result envs do not clobber each other.
- `BGJOB_STATUS=WAIT` must cause the next identical `bgjob wait` for that lane with no intervening prose or tools.
- `DONE` with `BGJOB_RC=timeout` or `BGJOB_RC=orphaned` must route to the lane's existing failure/skip branch (research lanes are best-effort).
- Stale per-lane merge-result env from a prior attempt must not satisfy required KVs after a fresh start; truncate before each lane start.
- Claude Agent fallback lanes are unaffected — only external (Codex/Cursor) lane launches migrate.

## Failure modes

- Two lanes reuse one `--step` slug and overwrite result envs mid-run.
- A lane prompt path continues on `DONE` without checking `BGJOB_RC`.
- Lane launcher stdout gains banners and breaks harness parsing.
- Allowlist rows removed while some research prose still requests `run_in_background`, causing `lint bg-wait-coverage` failure.

## Testing strategy

1. `bash scripts/test-research-structure.sh`
2. `python3 python/cli.py lint bg-wait-coverage`
3. Final validation: `make py-lint`, affected `test-harnesses-N` shards.

## Implementation notes

- Keep changed prompt literals covered by prompt-shape harnesses.
- Keep lane fallback and negotiation semantics unchanged; this chunk swaps only the launch/wait transport.
- Do not retire legacy hooks or defense docs; #6516 owns deletion.

## Acceptance

1. `git grep -l "run_in_background" skills/research/` returns nothing; the two research rows are removed from `python/larch/lint/bg_wait_allowlist.txt`; `python3 python/cli.py lint bg-wait-coverage` passes.
2. Research and validation lanes launch via per-lane `bgjob start` with unique `--step` slugs and chunked `bgjob wait`, with per-lane merge-env truncation (asserted in `scripts/test-research-structure.sh`, including the collision regression).
3. Claude Agent fallback behavior is unchanged.
4. `make py-lint` and all affected `test-harnesses` shards pass.

diff_added: 90
diff_deleted: 60
mechanical_churn: true
diff_lines: 150

## Test plan
(no test plan section in plan-file)
