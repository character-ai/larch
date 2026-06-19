## Goal
Implement issue #4790: [IMPLEMENTING] [BUG] Plan-review panel silently drops all reviewer findings….

## Implementation Plan
## Summary

The `/design` plan-review panel **silently drops every reviewer finding** and reports a false "clean" review. Reviewers run and produce findings, the collector records them all `STATUS=OK`, but `_compose_findings_from_collector` parses the collector output with the wrong delimiter, so every record is skipped. The loop then emits `LOOP_STATUS=complete` with `ACCEPTED_COUNT=0`, and the plan passes review without a single finding ever reaching the ballot.

## Original report

User request: "root cause analysis of all review process issues."

Context: during a `/design` run, the round-1 plan-review panel reported 0 findings and `complete`. Inspection showed the 8 reviewers actually produced ~12 findings (including a 7-of-8 consensus `[SCOPE-REDUCTION]` on the plan), yet none reached the ballot. Recent panel-dispatch failures were just fixed; this is a different, downstream failure on the collection/aggregation path.

## Reproduction scenario

1. Run `/design <issue>` to plan review (Step 3) with Codex and Cursor available, on a plan that draws real reviewer findings.
2. Let the panel dispatch and reviewers complete (the 8 reviewer `*-output.txt.tsv` sidecars contain findings).
3. Observe the loop envelope: `LOOP_STATUS=complete`, `ACCEPTED_COUNT=0`, `COLLECT_OK_COUNT=0`.
4. Inspect `$DESIGN_TMPDIR/collector-results.env`: all reviewers `STATUS=OK`. Inspect `$DESIGN_TMPDIR/ballot.txt`: 0 bytes. Inspect `plan-review/round-1/findings-classification.tsv`: header only.

Direct unit reproduction: call `plan_review_round._compose_findings_from_collector(design, collect_text, manifest)` with `collect_text` in the real `collect_results.py` `KEY=VALUE` format. It returns `ok_count=0` and empty findings.

## Reproduction scenario notes

This was observed in a live run, not forced. The artifacts above are preserved under a `/design` session tmpdir.

## Expected behavior

- The collector output is parsed; each `STATUS=OK` reviewer is counted and its sidecar TSV findings are extracted into the ballot.
- Reviewer findings reach voting and tally; accepted findings land in `accepted-plan-findings.md`.
- If zero reviewer records parse when reviewers were expected, the round is classified `degraded-empty-collector` (a loud, degraded outcome), never `complete`.

## Observed behavior

- `_compose_findings_from_collector` returns `ok_count=0` and empty findings even though 8 reviewers succeeded and produced ~12 findings.
- `ballot.txt`, `accepted-plan-findings.md`, and `oos.md` are empty; `findings-classification.tsv` is header-only.
- The loop reports `LOOP_STATUS=complete`, `DEGRADED_PANEL=0`, `ACCEPTED_COUNT=0`: a false clean. Gate C then presents the plan as having passed review with no findings.

## Root cause analysis

**Primary defect: collector output format mismatch.**

- `python/collect_results.py` emits each reviewer record as multi-line `KEY=VALUE` (`REVIEWER_FILE=`, `TOOL=`, `STATUS=`, `EXIT_CODE=`, `STRUCTURED_SIDECAR=`, `FAILURE_REASON=`), one field per line, via `record.fields()` then `_emit(field)` (collect_results.py:71-86, 959-960). It never emits the ASCII Unit Separator `\x1f`.
- `python/plan_review_round.py` `_compose_findings_from_collector` parses the same text as `\x1f`-delimited single-line records: it skips any line without `\x1f` (line 170) and splits on `\x1f` (line 172). Because no line contains `\x1f`, every record is skipped, so `ok_count=0` and the findings list is empty.
- The collection-failure guard at plan_review_round.py:382 makes the same `\x1f` assumption.

This looks like a sh-to-py migration regression: the Bash collector likely used `\x1f` field separators, the Python collector emits `KEY=VALUE`, but the Python consumer kept `\x1f` parsing. (Inference; not git-blamed.)

**Secondary defect: false-clean classification masks the empty collection.**

- plan_review_round.py:502 classifies `degraded-empty-collector` only when `accepted == 0 AND ok_count == 0 AND degraded`, where `degraded` is derived solely from voter dispatch (line 499). When collection yields zero parsed records but the voter panel dispatches fine (`degraded=False`), the run falls through to `LOOP_STATUS=complete` (line 514). So even a genuine zero-collector round is reported as clean.

**Why undetected.** No test exercises `_compose_findings_from_collector` or `execute_round` against real `collect_results.py` output. There is no `python/test_plan_review_round.py`; the only `\x1f` fixtures live in `test_progress_report.py` (a different consumer), so the tests match the broken parser instead of the real collector format.

## Evidence

- `$DESIGN_TMPDIR/collector-results.env` (verbatim collector stdout, written at plan_review_round.py:380): 8 records, each `STATUS=OK`, `EXIT_CODE=0`, with `STRUCTURED_SIDECAR=*.tsv`. KEY=VALUE, newline-delimited, blank-line between blocks.
- 8 reviewer `.tsv` sidecars under `plan-review/round-1/` hold ~12 findings (for example `codex-primary-plan-innovation` 2, `cursor-plan-pragmatic` 4; 7 of 8 reviewers flagged a `[SCOPE-REDUCTION]`).
- `ballot.txt` = 0 bytes; `accepted-plan-findings.md` = 0 bytes; `oos.md` = 0 bytes; `findings-classification.tsv` = header only.
- `round-summary.env`: `COLLECT_OK_COUNT=0`, `COLLECT_FAILURE_COUNT=0`, `LOOP_STATUS=complete`, `DEGRADED_PANEL=0`, `ACCEPTED_COUNT=0`. `COLLECT_OK_COUNT=0` directly contradicts the 8 `STATUS=OK` records in `collector-results.env`.
- `python/collect_results.py:71-86` (`fields()`), `:959-960` (`_emit(field)` per field). A `grep` for `\x1f` / `\037` / `chr(31)` in collect_results.py returns 0 matches.
- `python/plan_review_round.py:170,172` (`\x1f` skip + split), `:382` (same assumption), `:502-514` (degraded classification).
- No `python/test_plan_review_round.py`; no test references `_compose_findings_from_collector` or `execute_round`.

## Affected files

- `python/plan_review_round.py` (primary): `_compose_findings_from_collector` (142-252), `\x1f` parse (170, 172), failure guard (382), degraded classification (502-514).
- `python/collect_results.py` (contract counterpart, 71-86 and 959-960): likely correct; the consumer should match it.
- `python/progress_report.py:1814` (secondary consumer): uses the same `\x1f` split on collector output; may mis-render reviewer status. Needs a parity audit.
- Missing `python/test_plan_review_round.py`: the round executor has no unit coverage.

## Suggested fix(es)

1. Fix `_compose_findings_from_collector` and the guard at line 382 to parse `collect_results.py` `KEY=VALUE` blocks: split records on blank lines, read `KEY=VALUE` per line, map `REVIEWER_FILE` / `TOOL` / `STATUS` / `EXIT_CODE` / `STRUCTURED_SIDECAR` / `FAILURE_REASON`. Prefer fixing the consumer over the collector, since other consumers and the SKILL.md prose expect `KEY=VALUE`.
2. Harden classification: treat `ok_count == 0` (when the panel was not pruned-empty) as `degraded-empty-collector` regardless of voter `degraded`, so a real zero-collector round never reports `complete`.
3. Audit `python/progress_report.py:1814` for the same `\x1f` assumption and align it with the collector format.
4. Add `python/test_plan_review_round.py`: feed realistic `collect_results.py` `KEY=VALUE` output (with sidecar TSVs) through `_compose_findings_from_collector` / `execute_round`; assert findings parse, `ok_count` is correct, the ballot is non-empty, and a zero-OK round yields `degraded-empty-collector` rather than `complete`. Per `.claude/rules/launcher-argv-test-coverage.md`, format/contract changes need same-PR harness updates.

## Related issues

- #4724 (closed, [DONE], fixed by #4728): same symptom class ("Step 3 reviewers produce TSV but findings stay empty"), but a distinct root cause. #4724 was the pre-port Bash `plan-review-loop.sh` where the collection phase never completed and `.completed/step-3` was absent. In this bug collection succeeds (8 OK collector records; `.completed/step-3` and `.step3-review-result.env` are both written), and the drop is the `\x1f`-vs-`KEY=VALUE` parse mismatch in the ported Python `_compose_findings_from_collector`. Treat as a regression of the same failure class in the new in-process path, not a duplicate.
- #4632 (closed, [DONE]): sh-to-py G3 port that moved the Step-3 plan-review loop bodies in-process, where `plan_review_round.py` now lives. Likely origin of the format mismatch.
- #4747, #4765 (closed): other recent plan-review panel failures (dispatch `--mode`; slot prompt_file). Different root causes; listed for panel-reliability context.
- #4768 (open): plan-review panel should degrade gracefully when one slot row is invalid. Related degradation theme; the secondary defect here (zero parsed collectors falling through to `complete`) overlaps.

## Open questions

- Is the canonical collector contract `KEY=VALUE` (fix the consumer) or `\x1f` (fix the collector)? `collect_results.py` and the SKILL.md prose both point to `KEY=VALUE`, so fixing the consumer is the safer direction.
- The round-1 voter panel reported only 2 of 3 judges available ("unanimous-2" tier). With an empty ballot it was moot, but it may be a second, independent degradation worth confirming once findings actually reach the ballot.
- Was the `\x1f` parser introduced by the sh-to-py migration of the plan-review loop? A git blame on `python/plan_review_round.py` should confirm.

## Test plan
(no test plan section in plan-file)
