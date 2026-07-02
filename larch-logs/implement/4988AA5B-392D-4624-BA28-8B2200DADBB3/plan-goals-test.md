## Goal
Implement issue #6026: [IMPLEMENTING] [BUG] Empty-ballot degraded-vote banner triggers guaranteed-waste full panel retry.

## Implementation Plan
## Summary

When a review round produces zero in-scope findings, voter slots emit empty ballots, the parse-rate check fails them, and the tally writer emits degraded banners ("0 judges available", "narrative-only voter slot removed"). The round runner treats any degraded banner as cause to re-run the entire reviewer panel. On an empty ballot the retry deterministically reproduces the same degraded tally, so the run pays a full second panel wave and aggregator run for nothing.

## Original report

From the 2026-07-02 post-merge audit. In the #5972 run the round had 0 findings after pre-vote OOS drops, and the degraded retry re-ran all 8 reviewer slots plus the aggregator: two full waves, 7m49s of review wall time, roughly 13 dollars for a 53-line diff, with voting-tally-degraded-attempt-1.md byte-identical to the final voting-tally.md. The same banner shape appeared in the #5971 run (zero findings survived; nil impact beyond the banner) and the #5977 run (retry succeeded because real findings existed, which shows the retry is only useful when a ballot is non-empty).

## Reproduction scenario

Run /implement on a small clean diff where every review proposal is dropped as OOS before the vote (pre-vote-oos-gate.env FINDINGS_REMAINING=0, findings-classification.tsv header-only). Voter slots produce empty or unparseable ballots; the tally degrades; the round runner re-dispatches the full panel.

## Expected behavior

Zero-finding rounds short-circuit: no vote, no degraded banner, no panel retry. The degraded-tally retry fires only when there are findings to adjudicate.

## Observed behavior

- python/larch/review/review_tally.py:653-691: degraded banners emitted when eligible=1, parse_failed=1, effective=0; an empty voter file fails `_parse_rate_ok` (review_tally.py:218) even when the ballot itself is empty.
- python/larch/review/round_runner.py:475-506: any degraded banner triggers a full-panel re-run without checking whether any findings were on the ballot.
- Run log larch-logs/implement/7623E215-D6C5-4123-8334-D1EAB4B29278: attempt-1 tally byte-identical to final; timing chart shows two reviewer waves and two aggregator runs.

## Root cause analysis

The degraded-vote retry was designed for infrastructure failures on real ballots; the empty-ballot case satisfies the same degraded predicate because parse-rate validation treats an empty voter output as a parse failure rather than a valid empty vote. Pre-existing behavior, surfaced by the audit; not introduced by the audited PRs.

## Evidence

Cited code paths and committed run logs above, at 63ed17f18.

## Affected files

- python/larch/review/round_runner.py: retry gate.
- python/larch/review/review_tally.py: parse-rate handling for empty ballots and banner emission.

## Suggested fix(es)

- Gate the degraded retry on a non-empty ballot (skip when pre-vote findings remaining is zero).
- Or make an empty voter output for an empty ballot parse as a valid empty vote so the tally never degrades in that case.
- Keep the retry for degraded tallies on non-empty ballots (the #5977 run shows it recovering real value there).

## Open questions

- Should the "Manual adjudication needed" banner appear at all when there is nothing to adjudicate?

## Test plan
(no test plan section in plan-file)
