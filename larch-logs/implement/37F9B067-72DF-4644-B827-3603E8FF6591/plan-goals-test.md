## Goal
Implement issue #5939: [IMPLEMENTING] [BUG] Cursor/token cost-report: retro-fix rate divergence + 2 report-accuracy gaps.

## Implementation Plan
## Summary

The token/cost reporting subsystem (`python/larch/report/`) has three related accuracy defects surfaced by an audit of recently merged fixes (#5852 / #5853 / #5854 / #5871). The primary defect is a **money-math correctness bug**: the Cursor retro-fixer prices historical run-logs with a different rate formula than the live going-forward pricer, so committed cost text permanently disagrees with `/report-tokens`, and the retro-fixer's own test locks in the divergence. Two lower-severity defects ride along: the realized-cost instrumentation is blind to the design tier it was built for, and two comments/tests mis-cite the issue number.

## Original report

Audit of the last ~50 merged fixes found three accuracy defects in `python/larch/report/`, filed together as one issue, severity-ordered.

**DEFECT 1 (PRIMARY — correctness / money math):** The Cursor retro-fixer diverges from the going-forward pricer. `python/larch/report/retro_fix_cursor.py` (rate constants) applies the Cursor Teams surcharge **only to cache-read** and leaves input/output at the pre-surcharge $0.50 / $2.50. The live pricer `python/larch/report/report_tokens_cost.py` surcharges **all three** token classes for `composer-2.5`. So the human-readable cost text baked into committed run-logs (`final-summary.md` "Cursor $X") no longer matches `/report-tokens` for any run with nonzero input/output tokens. An audit corpus sweep found ~710 of 1168 committed cost lines mismatch, up to ~$2.77/run. The retro-fixer's own test `python/tests/report/test_retro_fix_cursor.py` pins the retro-fixer's un-surcharged output and never cross-checks the live pricer, so it locks in the divergence rather than catching it.

**DEFECT 2 (functional gap):** The realized reference-read cost instrumentation added by #5871 is blind to the design tier — its primary named target. `measure-realized-cost` reports design at exactly the SKILL.md token floor with `reference_tokens_per_invocation = 0.00` because committed design `larch-tokens-*.jsonl` transcripts carry no tool_use blocks. #5871's acceptance criteria are unmet on committed data.

**DEFECT 3 (trivial — traceability):** `report_tokens_scan.py` and `test_tokens.py` cite issue #5838 for the `totals.cache_read` null-serialization fix, which is actually #5852.

## Reproduction scenario

**Defect 1:**
1. Pick any committed Cursor run-log with nonzero input and output token counts (most `larch-logs/implement/*/final-summary.md` with a Cursor lane).
2. Compare the "Cursor $X" figure written by the retro-fixer against `python3 python/cli.py report-tokens analyze` (or the going-forward pricer in `report_tokens_cost.py`) for the same token buckets.
3. Observe the two figures differ because the retro-fixer omits the Teams surcharge on input and output.

**Defect 2:**
1. Run `measure-realized-cost` for the design skill.
2. Observe `tokens_per_invocation` equals `skill_md_tokens` exactly and `reference_tokens_per_invocation` is `0.00`.
3. Inspect committed design `larch-tokens-*.jsonl` and confirm no tool_use/tool_call blocks are present.

**Defect 3:** Read the two cited lines; the issue number in the comment/test name is #5838 but the behavior described is the #5852 cache_read fix.

## Expected behavior

- **Defect 1:** Historical (retro-fixed) Cursor cost text equals what `/report-tokens` and `report_tokens_cost.py` compute for the same token counts. A regression test asserts equality between the retro-fixer and the going-forward pricer.
- **Defect 2:** For design, `measure-realized-cost` counts non-zero reference reads (approval-gates.md, plan-review.md, finalize-step5.md) and reports design tokens exceeding the SKILL.md floor by roughly the eager-reference total — the acceptance criterion #5871 set for itself.
- **Defect 3:** Comments/test names cite #5852.

## Observed behavior

- **Defect 1:** Retro-fixer surcharges cache-read only; committed cost text is ~4-6% low on the input+output surcharge and permanently disagrees with the live pricer. The retro-fixer test pins the wrong (un-surcharged) number.
- **Defect 2:** Design is reported at the SKILL.md floor with 0 reference tokens — the exact blindness #5871 aimed to remove.
- **Defect 3:** Both sites cite #5838.

## Root cause analysis

- **Defect 1 (confirmed by direct read):** `retro_fix_cursor.py` hardcodes its own rate constants (`_INPUT_RATE = 0.50`, `_OUTPUT_RATE = 2.50`, `_NEW_CACHE_READ_RATE = 0.45`) instead of consuming the single source of truth used by `report_tokens_cost.py`, where the Teams surcharge (`CURSOR_TEAMS_TOKEN_RATE_SURCHARGE_PER_M`) is added to input, cache_read, and output of `composer-2.5`. The two pricing paths drifted; #5853 (retro) and #5854 (going-forward) landed with inconsistent formulas. The retro-fixer test asserts the retro path's own output, so it cannot catch the drift.
- **Defect 2 (reported by audit; mechanism plausible, re-confirm):** The parser only counts references it sees as tool_use reads in the session transcript. Committed design transcripts predate the design transcript-capture that #5871 added (`design_publish.py`), so there are no read events to count. The mechanism works on synthetic fixtures but has no real design data yet.
- **Defect 3:** Copy/paste of the neighboring #5838 attribution work into the #5852 cache_read change.

## Evidence

- `python/larch/report/retro_fix_cursor.py:33-35` — `_NEW_CACHE_READ_RATE = 0.45`, `_INPUT_RATE = 0.50`, `_OUTPUT_RATE = 2.50` (surcharge on cache-read only). Verified by direct read.
- `python/larch/report/report_tokens_cost.py` — comment near line 29 "Applies to input, cache-read, and output for composer-2.5"; `composer-2.5` rate = `CURSOR_COMPOSER_BASE[*] + CURSOR_TEAMS_TOKEN_RATE_SURCHARGE_PER_M` on input, cache_read, and output; base input = 0.75. Verified by direct read.
- `python/tests/report/test_retro_fix_cursor.py` — asserts the retro-fixer's own "Cursor $X" output; no cross-check against the going-forward pricer. (Audit finding.)
- Audit corpus sweep: ~710 / 1168 committed cost lines mismatch `/report-tokens`, up to ~$2.77/run (~$331 aggregate). (Audit computation; implementer should re-derive before quoting.)
- `python/larch/report/report_tokens_scan.py:92` — comment `(issue #5838)` on the totals.cache_read fallback. Verified by direct read.
- `python/tests/report/test_tokens.py:819` — `Regression test for issue #5838: external-vendor totals.cache_read must be [integer/non-null]` (the #5852 behavior). Verified by direct read.
- `measure-realized-cost` design output: `tokens_per_invocation == skill_md_tokens` (e.g. 24592.00 == 24592), `reference_tokens_per_invocation = 0.00`. (Audit finding via running the command; re-confirm.)

## Affected files

- `python/larch/report/retro_fix_cursor.py` — hardcoded rate constants that diverge from the live pricer (Defect 1).
- `python/tests/report/test_retro_fix_cursor.py` — test pins the divergent output; should assert equality with `report_tokens_cost.py` (Defect 1).
- `python/larch/report/report_tokens_cost.py` — the going-forward source of truth the retro path should consume (Defect 1).
- Committed `larch-logs/**/final-summary.md` cost lines — carry the divergent historical figures; a corrected retro-fix must be re-run over them (Defect 1).
- `python/larch/design/design_publish.py` and the `measure-realized-cost` reader — forward-looking design transcript capture that has no committed corpus yet (Defect 2).
- `python/larch/report/report_tokens_scan.py:92`, `python/tests/report/test_tokens.py:819` — mis-cited issue number (Defect 3).

## Suggested fix(es)

- **Defect 1:** Make `retro_fix_cursor.py` import/consume the same rate table and surcharge logic as `report_tokens_cost.py` (surcharge input + cache_read + output). Re-run the retro-fix over committed logs to correct the historical cost text. Change `test_retro_fix_cursor.py` to assert the retro-fixer's output equals the going-forward pricer for the same token buckets (a cross-consistency test, not a self-pinned literal).
- **Defect 2:** Either capture and commit at least one design run's transcript with tool_use blocks so `measure-realized-cost` can count design references, or adjust the acceptance/reporting so design is not silently reported at the floor with 0 references (make the "no data yet" state explicit rather than looking like a measured zero).
- **Defect 3:** Update both citations to #5852.

## Open questions

- Defect 1: Should historical run-logs be retro-corrected again (mutating many committed files), or should the divergence be accepted and only the go-forward path + a consistency test be fixed? This is a policy call for the maintainer given the blast radius on `larch-logs/`.
- Defect 2: Is committing a design transcript with tool_use blocks acceptable (size/PII), or should design realized-cost stay forward-looking with an explicit "not yet measured" sentinel?

## Test plan
(no test plan section in plan-file)
