# Review Round 1

- Mode: `diff`
- 7 accepted, 2 rejected (2 neutral)

## Accepted Findings

### FINDING_4: `_patch_ship_state_keys` can create patch-only `ship-pr-state.sh`
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `_patch_ship_state_keys` (`python/ship.py:826-840`) can write a single-key `ship-pr-state.sh` when the file is missing or empty. After disposition succeeds, `step8_oos_checkpoint_main` may stamp stats, set `step9a1=true`, create only `OOS_PENDING=false`, emit `NEXT_ACTION=reship`, and lose required re-entry keys — violating the no single-key wipe contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Fail when the state file is absent, empty, or would contain only patch keys, and route that as checkpoint bookkeeping failure.
  - From codex-specialist-edge-cases-output.txt: Fail closed when ship-pr-state.sh is absent or has no allowed existing keys before clearing OOS_PENDING, and route to the bookkeeping-failure stall path.


### FINDING_5: OOS checkpoint bookkeeping is not transactional for `run-statistics.md`
- **Reviewer(s)**: codex-specialist-correctness-output.txt, dyn-dyn-oos-checkpoint-output.txt
- **Severity**: important
- **Concern**: `_write_run_statistics` runs before manifest stamp and `OOS_PENDING` patch. If stamp or `_patch_ship_state_keys` fails, the handler emits `OOS_CHECKPOINT_RC=2` / `NEXT_ACTION=stall` while `run-statistics.md` remains as completion evidence and `OOS_PENDING` may stay `true`, leaving conflicting durable signals in the run log.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Publish run-statistics only after the full success tail succeeds, or delete it on bookkeeping failure before emitting stall.
  - From dyn-dyn-oos-checkpoint-output.txt: Write stats only after stamp and state patch succeed, or roll back/remove `run-statistics.md` on bookkeeping failure before emitting stall.


### FINDING_6: Stale Step 8 SKILL.md prose bypasses new checkpoint router
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `skills/implement/SKILL.md:854` still instructs direct `oos disposition-checkpoint` and success-marker handling outside `implement step-8-oos-checkpoint`. An orchestrator can follow it after OOS work, bypass `NEXT_ACTION` handling, and skip Python-owned stats/manifest/`OOS_PENDING` bookkeeping.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Rewrite the paragraph so oos file is provisional and only step-8-oos-checkpoint.sh owns disposition, stats, manifest stamp, and OOS_PENDING clearing.


### FINDING_9: OOS checkpoint success test mocks manifest stamp without asserting it
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Success-path OOS checkpoint test (`python/test_implement_dispatch.py:234-268`) mocks `_stamp_manifest` and never verifies `step9a1` stamping. A future edit could drop or reorder `_stamp_manifest` while CI still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Remove the stamp mock or use wraps; assert manifest.json has steps_ran.step9a1=true and optionally that _stamp_manifest was called with value=True.


### FINDING_10: Missing tests for `RUN_ID` resolution and bookkeeping failure paths
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-dyn-oos-checkpoint-output.txt
- **Severity**: important
- **Concern**: No test covers `RUN_ID` precedence when `ship-pr-state.sh` `RUN_ID` and `session-id` differ; stats/count could target the wrong run directory. The plan also called for separate stats-write and state-patch failure cases beyond manifest-stamp failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a test with conflicting RUN_ID vs session-id and ndjson only under the state RUN_ID path; assert stats/count use state-run.
  - From dyn-dyn-oos-checkpoint-output.txt: The plan called for a `RUN_ID` precedence test (state over `session-id`) and separate stats-write / state-patch failure cases; only manifest-stamp failure is covered today.


### FINDING_13: `_step8_oos_checkpoint_run_id` resolver incomplete vs disposition checkpoint
- **Reviewer(s)**: dyn-dyn-oos-checkpoint-output.txt
- **Severity**: important
- **Concern**: `_step8_oos_checkpoint_run_id` (`python/implement_dispatch.py:966-989`) resolves only `ship-pr-state.sh` `RUN_ID`, then `session-id`. It does not mirror `disposition_checkpoint_main`'s single-match `larch-logs/implement/*/oos-issues.ndjson` fallback. When state lacks `RUN_ID`, disposition can return rc `0` but bookkeeping gets `run_id=""` or wrongly uses tmpdir `session-id` (not the larch run log id), targets the wrong `larch-logs/implement/<id>/` tree, emits `OOS_CHECKPOINT_RC=2` / `NEXT_ACTION=stall`, and leaves `OOS_PENDING` set despite cleared disposition.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-oos-checkpoint-output.txt: Share one run-id resolver with `file_oos.disposition_checkpoint_main` (state → session-id → single ndjson parent basename), or derive `run_id` from the ndjson path disposition already selected, and add a harness where disposition passes without state `RUN_ID`.
  - From dyn-dyn-oos-checkpoint-output.txt: Do not treat `session-id` as `RUN_ID` for run-scoped artifacts unless they are known equal; prefer state `RUN_ID`, then single-ndjson parent basename, and fail bookkeeping with a explicit diagnostic if no canonical run id resolves.


### FINDING_14: Stale sentinel URLs can inflate filed count when ndjson is absent
- **Reviewer(s)**: dyn-dyn-oos-checkpoint-output.txt
- **Severity**: important
- **Concern**: When run-scoped `oos-issues.ndjson` is absent, `_step8_oos_checkpoint_filed_count` falls back to `_persisted_filed_evidence`, which also counts URLs from tmpdir-root `oos-issues-created.md`. After disposition rc `0` on an empty or ndjson-less batch, stale sentinel URLs can inflate `run-statistics.md` relative to what disposition validated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-oos-checkpoint-output.txt: When ndjson is absent, use `0` or the same disposition-side counting helper/gate output; only count sentinel URLs when ndjson is the authoritative evidence source for that run.


