### FINDING_1: Fail closed on a fresh pre-fix sentinel
- **Reviewer(s)**: Cursor-Arch, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: The new `.ship-pre-fix-rebase-ok` marker is only written, not consumed, so a stale or skipped pre-fix pass can still let `PRE_FIX_REBASE_REQUIRED=true` handoffs reach autonomous repair.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: `Add a named consumer: before autonomous repair (e.g. `ship-pr-ci-fix.md` precondition or a small Python guard invoked from Step 8+), require the sentinel when handoff has `PRE_FIX_REBASE_REQUIRED=true`; emit stall/`rc!=0` with no `NEXT_ACTION=` when absent; add regression coverage`
  - From Codex-Innovation: `Add a firm update to the Step 8 ci-fix path or this reference that requires the new `.ship-pre-fix-rebase-ok` marker when `PRE_FIX_REBASE_REQUIRED=true`, and fail closed before logs, edits, commits, or pushes when it is absent`
  - From Cursor-Pragmatic: `Add a named consumer: either a small Python guard invoked from the Step 8+ ci-fix/reship path, or an explicit SKILL/ship-pr-ci-fix precondition that refuses repair when the handoff requires pre-fix rebase and the sentinel is missing; add a regression test for the refuse path`
  - From Codex-Pragmatic: `Add skills/implement/SKILL.md or ship-pr-ci-fix.md updates that check the new sentinel before autonomous CI-fix and route to stall or tool-failure when it is absent`
  - From Cursor-Requirements: `Add a named consumer step in `ship-pr-ci-fix.md` and the Step 8 `ci-fix` branch in `skills/implement/SKILL.md`: after `ship pre-fix-rebase` returns `NEXT_ACTION=continue`, require a readable `.ship-pre-fix-rebase-ok` or route to stall/operator-bail with no `ship-pr-ci-fix.md` load`
  - From Cursor-Requirements: `Add a named consumer step in `ship-pr-ci-fix.md` and the Step 8 `ci-fix` branch in `skills/implement/SKILL.md`: after `ship pre-fix-rebase` returns `NEXT_ACTION=continue`, require a readable `.ship-pre-fix-rebase-ok` or route to stall/operator-bail without loading `ship-pr-ci-fix.md``
  - From Codex-Requirements: `Add firm updates to the Step 8+ `ci-fix` branch and matching references to require the sentinel after `ship pre-fix-rebase` returns `NEXT_ACTION=continue`; fail closed when `PRE_FIX_REBASE_REQUIRED=true` and the sentinel is absent, with a targeted regression harness for that branch`


### FINDING_2: Gate phase14 skip on no-checks metadata, not bare flag presence
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Ship Guard Auditor
- **Severity**: important
- **Concern**: The phase14 skip path can still be satisfied by a bare or conflict-shaped flag; it needs handoff metadata plus an explicit no-checks allowlist so conflict, empty, or handoff-only flags cannot bypass rebase routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: `Reorder guards as planned, then allow skip only when conflict metadata is absent and handoff/flag prove the no-checks-observed phase14 case (e.g. handoff `DETAIL=no-ci-checks-observed` plus non-empty structured flag, rejecting empty files and `REASON=postbump-rebase-conflict`); factor shared logic with `_ship_route_phase14_reship_pending` where possible; extend tests beyond `pending\n` fixtures`
  - From Cursor-Innovation: `Parse flag KV REASON before skip; allow skip only for no-checks reship reasons (mergeStateStatus=DIRTY or BEHIND); never skip when conflict handoff fields are present or REASON=postbump-rebase-conflict; add regression fixtures for each REASON`
  - From Cursor-Pragmatic: `Validate flag KVs before skip: require `RESUME_PHASE=ship-pr-rrr-phase14` and `REASON` matching the no-checks writer (`mergeStateStatus=DIRTY` or `BEHIND`); otherwise continue into the normal rebase path or fail closed`
  - From Cursor-Requirements: `Define an explicit allowlist for no-checks skip (e.g. parse flag KV lines and permit only no-checks `REASON` values while rejecting `postbump-rebase-conflict`), mirror `_ship_route_phase14_reship_pending` symlink exclusion, update `test_ship_pre_fix_rebase_phase14_flag_skips_rebase`, and add a regression that a postbump flag routes to conflict-fix or rebase instead of skip`
  - From Cursor-Requirements: `Define an explicit allowlist for no-checks skip (parse flag KV lines, permit only no-checks `REASON` values, reject `postbump-rebase-conflict`), mirror `_ship_route_phase14_reship_pending` symlink exclusion, update `test_ship_pre_fix_rebase_phase14_flag_skips_rebase`, and add a regression that a postbump flag does not take the skip branch`
  - From Cursor-dyn-Ship Guard Auditor: `Mirror `_ship_route_phase14_reship_pending` for pre-fix: require `.ship-route-exit-handoff.env` `DETAIL=no-ci-checks-observed` (or equivalent KV) plus an allowed flag (`REASON=mergeStateStatus=…` from `ship._write_phase14_flag`, `python/larch/implement/ship.py:192-197`); reject empty and conflict-only flags; keep conflict-metadata and in-progress rebase routing ahead of skip.`
  - From Cursor-dyn-Ship Guard Auditor: `Update the skip-success test to use a producer-faithful no-checks fixture (handoff `DETAIL=no-ci-checks-observed` plus allowed flag body) and add negative cases: empty flag and conflict `RESUME_PHASE`-only flag must not skip when branch/repo guards pass.`


### FINDING_3: Clear stale pre-fix sentinels on new handoff or entry
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Pragmatic, Cursor-Requirements, Codex-dyn-Ship Guard Auditor
- **Severity**: important
- **Concern**: Once a pre-fix run succeeds, the old `.ship-pre-fix-rebase-ok` can linger into a later handoff or retry unless the marker is explicitly cleared at handoff creation or entry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: `Clear the sentinel in `_write_ship_route_handoff` when setting `PRE_FIX_REBASE_REQUIRED=true` and again at `ship_pre_fix_rebase_main` entry; keep write-only-after-valid-terminal-decision; add tests that stale sentinel is absent until the current pre-fix attempt succeeds or legitimately skips`
  - From Codex-Arch: `Clear or version the sentinel at the start of each `ship pre-fix-rebase` invocation, write it only on valid `NEXT_ACTION=continue`, and update the ci-fix branch/reference to fail closed when `PRE_FIX_REBASE_REQUIRED=true` and the fresh marker is absent`
  - From Cursor-Pragmatic: `Unlink the sentinel at the start of `ship_pre_fix_rebase_main` (or at the first guarded entry), then write it only on the plan's allowed success/skip terminals; extend sentinel tests for stale-marker plus failed-guard cases`
  - From Cursor-Requirements: `In `_write_ship_route_handoff`, when appending `PRE_FIX_REBASE_REQUIRED=true`, unlink `$IMPLEMENT_TMPDIR/.ship-pre-fix-rebase-ok` (ignore missing), and add a regression test that a new handoff clears an old sentinel until pre-fix succeeds again`
  - From Cursor-Requirements: `In `_write_ship_route_handoff`, when appending `PRE_FIX_REBASE_REQUIRED=true`, unlink `$IMPLEMENT_TMPDIR/.ship-pre-fix-rebase-ok` (ignore missing), and add a regression test that a later consumer treat stale proof as current`
  - From Codex-dyn-Ship Guard Auditor: `Add firm updates to the Step 8 route docs or a Python helper used by those routes: clear or generation-tie the marker when PRE_FIX_REBASE_REQUIRED=true is written, then fail closed before ci-fix or reship if ship pre-fix-rebase returns continue but the fresh marker is absent.`


### FINDING_4: Preserve execution-issues data from both sources
- **Reviewer(s)**: Codex-Arch, Codex-Pragmatic
- **Severity**: important
- **Concern**: The final execution-issues summary can drop entries if it blindly prefers one artifact source over the other; when both run-dir NDJSON and tmpdir markdown exist, the richer set of entries needs to survive.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: `When both sources exist, merge parsed tmpdir markdown with run-dir NDJSON, or choose the source only after proving it contains all entries; add final-report coverage that both NDJSON and tmpdir-only entries appear`
  - From Codex-Pragmatic: `Parse tmpdir markdown first and use it only when it yields entries; otherwise fall back to run-dir NDJSON. Add a both-artifacts heading-only regression test`


### FINDING_6: Wire test-write-final-report into CI shards
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: The standalone final-report harness still isn't exercised by CI, so adding the Makefile prerequisite alone does not prove the script runs under shard coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: `Change the plan to wire the bash harness itself, either by updating `test-write-final-report` to run `bash skills/implement/scripts/test-write-final-report.sh` under `timing harness-mark` or by adding a dedicated shard prerequisite for that script`


### FINDING_8: Persist REBASE_COUNT after successful rebases
- **Reviewer(s)**: Cursor-Pragmatic, Codex-dyn-Ship Guard Auditor
- **Severity**: important
- **Concern**: Successful rebases can still leave the cap counter stale if the `RebaseResult.rebased` signal is not used to persist the updated count.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: `Mirror `ship_merge._ship_phase14_rebase`: capture `RebaseResult`, increment only when `result.rebased` is true, and persist via `_write_ship_state`/`_patch_ship_state_keys` while preserving existing iteration/fix_attempts/transient_retries fields`
  - From Codex-dyn-Ship Guard Auditor: `After a successful `rebase_and_push` with `result.rebased` true, increment and persist `REBASE_COUNT`, or centralize counter updates inside `rebase_and_push` for all callers.`


### FINDING_1: Missing freshness guard in Step 8 routing
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: important
- **Concern**: The Step 8 routing reference still lets `NEXT_ACTION=continue` reach ci-fix/reship without a `.ship-pre-fix-rebase-ok` freshness check, and the missing-sentinel path can end up in operator-bail instead of the intended post-driver stall handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Pin the guard to post-driver stall only (Step 16 with STALL_TRACKING, then Step 18), matching existing NEXT_ACTION=stall handling; do not use operator-bail for this mechanical failure
  - From Codex-Arch: Add the same PRE_FIX_REBASE_REQUIRED plus .ship-pre-fix-rebase-ok fail-closed check to the reship and ci-fix branch semantics in ship-pr-exit-matrix.md, or make that reference defer explicitly to the SKILL.md guard before continuing.
  - From Codex-Innovation: Update ship-pr-exit-matrix.md reship and ci-fix branch semantics to require the same sentinel check when PRE_FIX_REBASE_REQUIRED=true before stale-handoff clear or loading ship-pr-ci-fix.md.
  - From Cursor-Pragmatic: A `### UPDATED:` `skills/implement/references/ship-pr-exit-matrix.md` entry: after `ship pre-fix-rebase` returns `NEXT_ACTION=continue`, require `.ship-pre-fix-rebase-ok` when `PRE_FIX_REBASE_REQUIRED=true` before stale-handoff clear or `ship-pr-ci-fix.md`; stall/operator-bail if absent. Mirror on `reship`.
  - From Codex-Pragmatic: Add the same no-checks REASON allowlist, conflict-metadata routing, and PRE_FIX_REBASE_REQUIRED plus sentinel guard to this reference, matching SKILL.md and dispatch_ship.


### FINDING_3: Execution-issue loader drops committed rows
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: The execution-issues resolver still treats non-empty tmpdir markdown as a replacement for run-dir NDJSON, but flushes can clear `execution-issues.md` after writing NDJSON, so later tmpdir-only failures can cause the final report to drop previously committed rows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Change the helper plan to merge run-dir NDJSON groups with non-empty tmpdir markdown groups, or parse both and choose the richer combined result by event identity/count. Keep NDJSON-only and empty-tmpdir fallback.
  - From Codex-Innovation: Merge run-dir NDJSON and non-empty tmpdir markdown when both exist, with dedupe if needed. Keep the NDJSON fallback only when tmpdir markdown is absent or empty.
  - From Codex-Pragmatic: When both sources exist and tmpdir markdown is non-empty, parse both and merge/dedupe detail groups, with NDJSON-only fallback for empty markdown and degraded legacy rows preserved.
  - From Codex-Requirements: When both artifacts exist, parse both and merge or collapse by dedupe key; only fall back to one source when the other is absent or empty. Update the planned tests to assert the union.


### FINDING_4: Phase14 skip trusts stale metadata
- **Reviewer(s)**: Codex-Arch, Cursor-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: The allowlisted phase14 skip can still trust stale or incomplete handoff metadata, so a later `ci-fix` handoff can bypass the guarded rebase or a legitimate no-checks reship can stall because the freshness sentinel was not written on the valid skip path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Require both RESUME_PHASE=config.SHIP_PR_RRR_RESUME_PHASE and an allowlisted REASON before skip. Treat missing or mismatched RESUME_PHASE the same as empty, bare, conflict-shaped, or disallowed flags.
  - From Cursor-Pragmatic: Unify contract language: write `.ship-pre-fix-rebase-ok` on physical rebase success, allowlisted phase14 skip (`PRE_FIX_REBASE_STATUS=skip`), and conflict-fix routing. Keep regression tests explicit for the skip branch.
  - From Codex-Requirements: Allow the phase14 skip only when the current `.ship-route-exit-handoff.env` proves `NEXT_ACTION=reship` for `DETAIL=no-ci-checks-observed` plus the allowlisted flag reason, or clear the phase14 flag on every non-no-checks handoff.


### FINDING_5: Exec-issue Python tests are not superset fixtures
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The Python precedence tests use disjoint tmpdir and NDJSON fixtures, so they do not model a flushed-superset case and can encode dropping committed NDJSON rows instead of preserving post-flush appends.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Model superset fixtures: markdown contains flushed NDJSON content plus newer tmpdir-only rows. Assert combined counts/listings include both committed and post-flush entries; keep empty-markdown NDJSON fallback coverage separate.


### FINDING_6: Exec-issue shell harness expects wrong precedence
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The bash write-final-report harness still asserts a single-source dual-artifact precedence, so once the loader prefers non-empty tmpdir markdown the CI-facing summary check will fail or codify the wrong counts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add `### UPDATED: skills/implement/scripts/test-write-final-report.sh`: revise the dual-artifact block to expect tmpdir markdown counts when both files exist; keep the existing NDJSON-only fallback case after removing markdown; add a second dual-artifact case if both sources must contribute to the summary


