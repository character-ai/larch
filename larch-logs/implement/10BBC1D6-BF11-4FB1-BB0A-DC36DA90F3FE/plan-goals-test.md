## Goal
Implement issue #7404: [IMPLEMENTING] [BUG] [TRIAGED] Architectural assessment re-triggered by larch-log flush commits when diff fingerprint is unchanged.

## Implementation Plan
## Summary

When a larch-log flush commit advances HEAD between an architectural assessment submit and the next ship-bgjob check, the ship driver requests a full re-assessment even though the implementation diff fingerprint is unchanged. The coverage-advance mechanism (`_advance_note_coverage`) exists for exactly this case but fails to fire, causing an unnecessary subagent spawn, token cost, and run latency.

## Original report

During /implement run BA7BF6F8 for #6990, every larch-log flush commit (chore: flush ...) changed HEAD SHA but left the architectural diff fingerprint identical. The ship driver still required a full re-assessment (spawn `larch:arch-assessor` subagent, materialize, submit) each time, even though no source code changed. Observed once concretely: after a larch-logs flush at HEAD `0087c512`, `ASSESSMENT_KIND_INVARIANTS_DIFF_FINGERPRINT` and `ASSESSMENT_KIND_GUIDELINES_DIFF_FINGERPRINT` were the same as the prior assessment round. This caused unnecessary subagent spawns and token cost (~$4+ per wasted round).

## Reproduction scenario

1. Run `/implement` on any issue; reach the Step 8 assessments route.
2. Submit clean `invariants` and `guidelines` assessments at HEAD `A`.
3. A larch-log flush commit advances HEAD to `B` (only `larch-logs/` files changed).
4. Re-launch `step-8-ship.sh`.
5. Observe: ship bgjob returns `NEEDS_USER_REASON=architectural-assessments, DETAIL=invariants,guidelines`, requiring a full re-assessment even though the diff fingerprint is unchanged.
6. Manually run `python/cli.py architectural-assessment materialize --kind invariants --kind guidelines`: returns `ASSESSMENT_PENDING_KINDS=invariants,guidelines`, confirming both are considered pending.

## Expected behavior

`note_consumable` advances coverage via `_advance_note_coverage` when HEAD changes only in out-of-scope paths (i.e., all files in `git diff A..B` satisfy `_path_out_of_scope`). `larch-logs/**` is explicitly recognized as out-of-scope in `_path_out_of_scope` (line 997-998 of `python/larch/core/architectural_guidelines.py`). Assessment should be reused without a subagent spawn.

## Observed behavior

The ship driver treats the HEAD change as a stale assessment, emits `NEEDS_USER_REASON=architectural-assessments`, and requires a full re-assessment cycle (materialize → subagent → submit).

## Root cause analysis

`_advance_note_coverage` in `python/larch/core/architectural_guidelines.py` (line 1077) should handle this: it checks `_incremental_paths_out_of_scope(old_head=A, new_head=B)`, and if all changed paths are out-of-scope, it recomputes the live diff and advances the `COVERED_DIFF_FINGERPRINT`. However, the function fails before returning `True` in at least the following conditions:

- **Snapshot validation failure** (`_snapshot_matches`, line 1106): the snapshot file at `$IMPLEMENT_TMPDIR/architectural-invariant-materialized-diff.txt` must have the exact fingerprint stored in `COVERED_DIFF_FINGERPRINT`. If an intermediate materialize call or any other writer overwrote the snapshot between the prior submit and the `_advance_note_coverage` call, this check fails and coverage advancement silently returns `False`.
- **Note format mismatch** (`_note_identity`, line 610): if the durable note env was written in the legacy format (without `NOTE_STATE`, `AUTHORED_DIFF_FINGERPRINT`, `COVERED_DIFF_FINGERPRINT` keys), `_note_identity` may return `None` when `authored_fingerprint` or `covered_fingerprint` are empty (line 623-624), causing `_advance_note_coverage` to fail at line 1088-1089.

The exact failure point in this run was not confirmed but the re-assessment request was unambiguous.

## Evidence

- During run BA7BF6F8, assessed invariants+guidelines at HEAD `469ae440` with `DIFF_FINGERPRINT=57eb8c02f4abe93173fd5645ae5b3fc9c30fd401679d17d9a06c13351a06d68f`.
- Larch-log flush advanced HEAD to `0087c512` (only `larch-logs/implement/BA7BF6F8.../` files changed).
- Ship bgjob returned: `NEEDS_USER_REASON=architectural-assessments DETAIL=invariants,guidelines`.
- Materialize at `0087c512` returned: `ASSESSMENT_PENDING_KINDS=invariants,guidelines` and `DIFF_FINGERPRINT=57eb8c02f4...` (identical to prior round).
- `_path_out_of_scope`: `larch-logs/` is recognized (line 997-998) as always out-of-scope.
- `_incremental_paths_out_of_scope` (line 1018): would return `True` for a larch-log-only commit delta.
- `_advance_note_coverage` (line 1077): exists to handle this case but failed to fire.

## Affected files

- `python/larch/core/architectural_guidelines.py`: `_advance_note_coverage`, `_note_consumable`, `_snapshot_matches`, `_note_identity`
- `python/larch/implement/architectural_assessment.py`: `_already_handled`
- `python/tests/implement/test_architectural_assessment.py` (or equivalent): missing coverage for larch-log-only HEAD advance

## Suggested fix(es)

1. Add a regression test: submit an assessment, advance HEAD with a larch-log-only commit, call `note_consumable` (or `materialize`), and assert `ASSESSMENT_PENDING_KINDS` is empty.
2. Instrument `_advance_note_coverage` to emit a debug-level reason on each early return so the failure path can be diagnosed without a full test run.
3. If `_snapshot_matches` is the failure: ensure `submit` atomically updates the snapshot path in addition to the durable note env so the snapshot always matches `COVERED_DIFF_FINGERPRINT` after a successful submit.
4. If note format is the failure: ensure `submit` always writes the new format (with `NOTE_STATE`, `AUTHORED_DIFF_FINGERPRINT`, `COVERED_DIFF_FINGERPRINT`) so `_note_identity` never falls back to legacy format for fresh notes.

## Open questions

- Which early-return branch in `_advance_note_coverage` fires for a larch-log-only HEAD advance?
- Does `ship pr` internally call `materialize` (overwriting the snapshot) before checking `note_consumable`? If so, the snapshot would already be fresh and `_snapshot_matches` should pass — which would implicate a different failure branch.
- Is there a test for `_advance_note_coverage` covering the larch-log-only delta case?

<!-- larch:triage:start -->
## Triage

**Verdict: valid.** The wasted re-assessment is real. The reuse mechanism exists and is reachable, but it did not protect the run. Both root-cause hypotheses in the report are contradicted at the recorded main SHA. The evidence points at an unresolved-path comparison instead.

### Summary

A larch-log-only flush commit advances HEAD but cannot change the implementation diff fingerprint: the materialized diff excludes `larch-logs/**` (`python/larch/core/architectural_guidelines.py:304`). `_advance_note_coverage` (line 1077) exists to reuse the assessment in this case, and the ship gate reaches it with `repo_root` set. The run still looped into full re-assessments.

### Verified behavior

- Run BA7BF6F8 (issue #6990, PR #7397): the committed `ship-route-exit-handoff.env` ends with `NEXT_ACTION=assessments` and `DETAIL=invariants,guidelines`. Observation.
- Both committed outcome sidecars record clean assessments at HEAD `71599c43`, a later round than the report's `469ae440`. Repeated assessment rounds are consistent with the report. Observation.
- The ship gate calls `note_consumable` with `repo_root` (`python/larch/implement/ship_guidelines.py:372`, `:510`), so coverage advance is reachable on HEAD advance. Observation.

### Corrected root cause

The report's two candidate branches do not hold on main `18d374da`:

- **Legacy note format (`_note_identity` returns None): contradicted.** `_write_compose_materialization_metadata` writes `NOTE_STATE`, `AUTHORED_DIFF_FINGERPRINT`, `COVERED_DIFF_FINGERPRINT`, and `ASSESSED_HEAD_SHA` into the materialize env, and `_write_compose_assessment` passes them through to the durable note env. Standard-path notes are new-format. Observation.
- **Snapshot overwrite breaking `_snapshot_matches`: not supported.** A flush-only overwrite reproduces the same fingerprint, so the check still passes. The consumable check also runs before any re-materialization in both `_prepare_kind` and the ship gate. Observation.

Evidence-backed defect: `_validated_note_metadata` rejects the note when `Path(declared_snapshot) != expected_snapshot` (line 1070) with no symlink resolution. The sibling `validate_materialization` resolves both sides before comparing. Callers disagree on the `$IMPLEMENT_TMPDIR` form: `architectural_assessment.materialize()` and `submit()` resolve it (`python/larch/implement/architectural_assessment.py:593-594`, `:628-629`), while the ship gate uses the raw form (`python/larch/implement/ship_guidelines.py:517`). On macOS, `/tmp` resolves to `/private/tmp`, so both forms coexist for a tmpdir under a symlinked segment. A checker whose form differs from the recorded `DIFF_SNAPSHOT` fails closed into re-assessment before `_advance_note_coverage` runs, with the fingerprint unchanged. This reproduces the report's step 6 exactly: `materialize` (resolved form) reports pending kinds for a note recorded through the unresolved gate path. Observation for the code paths; inference that this branch fired in run BA7BF6F8.

### Immutable-main evidence

SHA `18d374da17ec57b0279f4f7958ee86d080051eb9` (`refs/heads/main`).

- `python/larch/core/architectural_guidelines.py:304`: the materialized diff excludes `larch-logs/**`.
- `python/larch/core/architectural_guidelines.py:997`: `_path_out_of_scope` recognizes `larch-logs/`, as cited.
- `python/larch/core/architectural_guidelines.py:1070`: unresolved `DIFF_SNAPSHOT` comparison.
- `python/larch/core/architectural_guidelines.py:1077`: `_advance_note_coverage`, as cited.
- `python/larch/implement/architectural_assessment.py:593-594`, `:628-629`: `materialize()` and `submit()` resolve the tmpdir.
- `python/larch/implement/ship_guidelines.py:517`: the ship gate keeps the raw tmpdir form.
- `larch-logs/implement/BA7BF6F8-9DA4-4DDD-B65D-CD6BA50B5617/ship-route-exit-handoff.env`: `NEXT_ACTION=assessments`.

### Reproduction

Not executed. No fixed `triage probe` covers this scenario. Proposed regression: submit an assessment, add a larch-log-only commit, and assert `materialize` reports no pending kinds. Add a variant that writes the durable env with an unresolved tmpdir and checks with the resolved form through a symlinked tmpdir fixture.

### Scope split

One issue. The fix lands in `python/larch/core/architectural_guidelines.py`, possibly `python/larch/implement/ship_guidelines.py`, plus tests. No dependency edges: no overlapping open issue (#7417 covers an unrelated ARG_MAX crash).

### Missing evidence

- The failing caller in run BA7BF6F8 is not identifiable from committed logs; tmpdir artifact bytes are not committed.
- The report's fingerprint value `57eb8c02f4...` and HEADs `469ae440` and `0087c512` are reporter-observed session values, not present in committed logs.
- `python/tests/core/test_architectural_guidelines.py` exceeds the 64KB inspect cap. No coverage-advance test was found in the inspected portions of either test file, so a tail test may exist.

### Fix outline

1. Compare `DIFF_SNAPSHOT` with both sides resolved in `_validated_note_metadata`, mirroring `validate_materialization`, or canonicalize `$IMPLEMENT_TMPDIR` once at every entry point, including the ship gate.
2. Emit a debug reason on each early return of `_advance_note_coverage` and `_validated_note_metadata` (keeps the report's suggestion 2).
3. Add the regression tests above (report suggestion 1, extended with the mixed path-form variant).
4. Drop report suggestions 3 and 4: submit already updates the snapshot and env together, and standard-path notes are already new-format.
<!-- larch:triage:end -->

## Test plan
(no test plan section in plan-file)
