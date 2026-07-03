## Plan

## Approach

Implement the documented accepted-only cumulation contract for `/design` Step 3 plan review across **both** places that reset these artifacts: the normal per-round tally pass (`plan_review_tally.py`) and the zero-findings short-circuit (`plan_review_round.py`). Plan review confirmed the original reproduction scenario (round 2 = `zero-findings-degraded-panel`) hits the short-circuit path, not the tally path, so both must change together or the reported bug persists.

Keep these files per-round only:

- `accepted-plan-findings.md`
- `rejected-findings.md`
- `oos.md`
- `voting-tally.md` (short-circuit path only; unchanged)

Make these files cumulative across automatic continuation rounds, in both the tally path and the zero-findings short-circuit path:

- `accepted-plan-findings-all.md`
- `oos-accepted-design.md`

Use exact-block de-duplication. Preserve prior block order. Append only new current-round blocks. Do not key only on `FINDING_N` or `OOS_N`, because IDs can repeat across rounds.

Do not change manual Gate A/C re-entry cleanup. That cleanup must still delete cumulative artifacts before a fresh manual review run.

## Files to modify/create

### UPDATED: python/larch/review/plan_review_tally.py

Add small helpers near `_append`:

- Read existing artifact text only when the path is a regular file.
- Split or normalize markdown artifact blocks by `### FINDING_...` / `### OOS_...` headings.
- Append unique chunks to a cumulative file while preserving prior text.

Update `_Tally.run` / `_render` flow:

- Continue blanking `accepted-plan-findings.md`, `rejected-findings.md`, and `oos.md` at each tally pass.
- Stop treating `oos-accepted-design.md` as a per-round blanked artifact.
- Add `accepted-plan-findings-all.md` as the cumulative accepted in-scope artifact.
- When `_render` produces `accepted_chunks`, write them to `accepted-plan-findings.md` and append unique chunks to `accepted-plan-findings-all.md`.
- When `_render` produces `oos_accepted_chunks`, append unique chunks to `oos-accepted-design.md`.
- Leave the `main-agent-vote-required` path with no new append. It should also not erase prior cumulative content.
- Keep tally-error behavior fail-closed for current-round artifacts, without clearing cumulative accepted files.

### UPDATED: python/larch/review/plan_review_round.py

Plan review found that `_reset_zero_findings_tally_artifacts` (called from `execute_round`'s zero-findings short-circuit at both call sites, lines ~846 and ~989) independently blanks `oos-accepted-design.md` before returning `LOOP_STATUS=zero-findings-degraded-panel`. This is the exact path the original bug hit in round 2, so it must change alongside the tally fix:

- Remove `oos-accepted-design.md` from the artifact-blank loop in `_reset_zero_findings_tally_artifacts`.
- Continue clearing only the per-round artifacts there: `accepted-plan-findings.md`, `rejected-findings.md`, `oos.md`, and refreshing `voting-tally.md`.
- Do not add `accepted-plan-findings-all.md` to this function's blank list; it is not blanked there today and must stay that way.

### UPDATED: python/tests/review/test_plan_review_round.py

`test_execute_round_zero_findings_clears_stale_tally_artifacts` currently asserts `oos-accepted-design.md` is empty after the short-circuit, encoding the buggy contract. Revise it:

- Seed `oos-accepted-design.md` and `accepted-plan-findings-all.md` with prior round-1 content before calling `execute_round`, alongside the existing seeded per-round files.
- Keep the existing assertions that `accepted-plan-findings.md`, `rejected-findings.md`, and `oos.md` are cleared.
- Replace the assertion that `oos-accepted-design.md` is empty with an assertion that it still contains the seeded round-1 content; add the same preserved-content assertion for `accepted-plan-findings-all.md`.

### UPDATED: python/tests/review/test_plan_review.py

Add regression coverage near existing tally artifact tests, covering the tally-level accumulation path (this covers `plan_review_tally.py`; the round-level short-circuit path is covered separately in `test_plan_review_round.py` above).

Test shape:

1. Run `plan-review tally` for round 1 with at least one accepted `FINDING_1` and one accepted non-security `OOS_1`.
2. Assert:
   - `accepted-plan-findings.md` contains the round-1 finding.
   - `accepted-plan-findings-all.md` contains the round-1 finding.
   - `oos-accepted-design.md` contains the round-1 OOS.
3. Run `plan-review tally` for round 2 using the same design tmpdir and a ballot/votes that produce zero accepted items.
4. Assert:
   - `accepted-plan-findings.md` is empty or lacks the round-1 finding.
   - `accepted-plan-findings-all.md` still contains the round-1 finding.
   - `oos-accepted-design.md` still contains the round-1 OOS.
   - `rejected-findings.md` and `oos.md` remain current-round artifacts, not cumulative.
5. Re-run the same accepted round or same current chunks once, and assert cumulative files do not duplicate exact blocks.

### MAY_UPDATE: skills/design/references/plan-review.md

Only update if implementation names or semantics differ from the current text.

Preferred path: keep the documented contract true by implementing functional equivalents of `_accumulate_round_accepted_all` and `_accumulate_round_oos`. If helper names differ, either avoid mentioning private helper names in prose or align the helper names.

## Edge cases

- A later zero-finding round must not erase prior accepted OOS or accepted in-scope findings, whether it goes through the normal tally path or the `execute_round` zero-findings short-circuit.
- A `main-agent-vote-required` tally must not append tentative content and must not erase prior cumulative content.
- Manual Gate A/C re-entry must still clear cumulative files through existing `step3-state --direct-review-entry` cleanup.
- Repeated tally of the same round must not duplicate exact cumulative blocks.
- Round-local files must still reflect only the current round, in both the tally path and the short-circuit path.

## Failure modes when non-trivial

- If de-duplication keys only on `FINDING_N`, later rounds can lose distinct findings with reused IDs.
- If `oos-accepted-design.md` is cleared by either the tally path (`plan_review_tally.py`) or the zero-findings short-circuit path (`plan_review_round.py`), accepted OOS can be lost before Step 5b; both call sites must be fixed together or the original bug persists.
- If cumulative files are updated before successful render, tally errors can persist partial findings.
- If regression tests only exercise `plan-review tally` directly, they can pass while the real `execute_round` zero-findings short-circuit still regresses, missing the actual reported bug.

## Testing strategy

Run focused Python tests:

```bash
python3 -m pytest python/tests/review/test_plan_review.py -k 'tally_plan_review'
python3 -m pytest python/tests/review/test_plan_review_round.py -k 'zero_findings'
```

If available and fast enough, also run:

make py-test

At minimum, run the new/revised regression tests in both files and existing nearby tally and round tests.

## Difficulty

This is workflow-affecting Step 3 artifact state, spanning two runtime modules (`plan_review_tally.py` and `plan_review_round.py`) and two test files, but each change is small and localized. The resolved scope avoids Step 5b warnings and rejected/OOS cumulation.

## Acceptance

Run focused Python tests:

```bash
python3 -m pytest python/tests/review/test_plan_review.py -k 'tally_plan_review'
python3 -m pytest python/tests/review/test_plan_review_round.py -k 'zero_findings'
```

If available and fast enough, also run:

make py-test

At minimum, run the new/revised regression tests in both files and existing nearby tally and round tests.

review_status: ok
rounds_completed: 2
difficulty: MODERATE
diff_lines: 220
