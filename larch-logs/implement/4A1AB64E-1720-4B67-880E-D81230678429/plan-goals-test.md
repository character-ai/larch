## Goal
Implement issue #4849: [IMPLEMENTING] [BUG] /design Step 3 reports already-applied findings as Unimplemented Suggestions.

## Implementation Plan
## Summary

In `/design` Step 3 plan review, findings that were **accepted and applied** in an earlier review round can re-surface in the final `rejected-findings.md` and be emitted at Step 4 under the heading `## Unimplemented Plan Review Suggestions`. The operator is told that already-applied improvements were not made. The existing cross-round convergence dedup (#4808) reconciles the *continuation decision* against the applied-finding ledger, but the *rejected-findings report* is not reconciled, so re-raised-then-rejected findings still appear as unimplemented at the Gate C decision point.

This is distinct from #4841 (dynamic scout-slot prompt scaffolding). Round 2 here used only static slots, which receive the plan path. It is the reporting-surface follow-up to the continuation-decision fix in #4808.

## Original report

Observed during a live `/design` run (larch 51.1.9) on issue #4835. Round 1 plan review accepted and applied 18 findings (the loop revised `plan.txt` via `revise-waterfall`, e.g. it removed the dependency-edge "flip" rule). The continuation heuristic then ran round 2, which re-raised the same set of findings against the revised plan and accepted 0 (18 neutral, 5 rejected). At Step 4 the run printed `## Unimplemented Plan Review Suggestions` listing ~23 findings, ~18 of which had in fact been implemented in round 1, including `FINDING_1: In-flight flip writes Y blocked by X` whose proposed resolution ("do not auto-flip") was already applied. This actively misled the Gate C final-approval decision in real time.

## Reproduction scenario

1. Run `/design <issue>` on a non-trivial feature so Step 3 plan review runs at least 2 rounds.
2. Let round 1 accept and apply one or more findings (the in-loop controller revises `plan.txt` and records keys in `$DESIGN_TMPDIR/.step3-applied-finding-keys.tsv`).
3. The continuation heuristic runs round 2 (round 1 had new high / non-nit accepted findings, so `PLAN_REVIEW_CONTINUE=true`).
4. Round 2 re-raises overlapping findings (some already applied in round 1) and accepts 0 of them; re-raised findings land NEUTRAL or REJECTED.
5. Compare the Step 4 `## Unimplemented Plan Review Suggestions` output and `$DESIGN_TMPDIR/rejected-findings.md` against `$DESIGN_TMPDIR/.step3-applied-finding-keys.tsv`. Findings present in the applied ledger appear in the "unimplemented" report.

Committed run-log artifacts for the observed occurrence are under `larch-logs/design/89BBAC3E-A53D-4E0F-8028-A627EB3BE366/` on `main`.

## Expected behavior

The Step 4 `## Unimplemented Plan Review Suggestions` report should exclude (or clearly annotate) findings whose normalized key already appears in the cumulative applied-finding ledger (`.step3-applied-finding-keys.tsv`). A finding applied in round 1 must not be reported as unimplemented just because a later round re-raised and rejected it.

## Observed behavior

The final `rejected-findings.md` reflects only the last round (round 2 overwrites earlier rounds) and is emitted verbatim as "Unimplemented Plan Review Suggestions". Because round 2 re-raised round 1's already-applied findings and rejected them as now-moot, ~18 applied findings are reported as unimplemented. The final `plan.txt` contradicts the report (for example it states "Do **not** auto-flip client and blocker", yet the report lists "remove the flip" as an unimplemented suggestion).

## Root cause analysis

- The continuation logic `plan_review_continuation` (`python/plan_review.py`, around line 1125) reconciles accepted findings against the applied-finding ledger for the **continuation decision only** (#4808, comment around line 1156): it calls `_read_applied_finding_keys` (line 1088) plus `_finding_dedup_key` to compute `new_flags` / `new_count` and stop the loop when re-raised findings are not genuinely new. This part works; the loop correctly stopped after round 2.
- That same reconciliation is **not** applied to `rejected-findings.md`. The per-round tally writes `rejected-findings.md` and the last round overwrites it; the Step 3b tail wrapper (`skills/design/scripts/design-step3b-tail.sh`, lines 107-111) simply `cat`s `$DESIGN_TMPDIR/rejected-findings.md` between the `---LARCH-REJECTED-BEGIN/END---` markers with no applied-key filter; `skills/design/SKILL.md` (around line 745) re-emits that body under `## Unimplemented Plan Review Suggestions`.
- Net: a finding accepted+applied in round 1, then re-raised and not-accepted in round 2, lands in the final rejected report and is presented to the operator as unimplemented.
- Secondary / unconfirmed: round-2 reviewers re-raised findings whose text describes the pre-revision (v1) plan (for example the flip at `plan.txt:33-37`) even though `plan.txt` had already been revised to v2 (no flip). Whether round-2+ reviewers receive the current revised `plan.txt` vs a stale snapshot, or re-derive findings from the scope anchor / issue narrative, could not be confirmed because the round-2 per-reviewer prompts/outputs were not in the published run log. This drives the volume of moot re-raised findings and a full wasted review round (5 reviewers + 3 voters + aggregator + tally for 0 net plan change).

## Evidence

- `larch-logs/design/89BBAC3E-A53D-4E0F-8028-A627EB3BE366/plan-review/round-1/round-summary.env`: `ACCEPTED_COUNT=18`.
- `.../.step3-applied-finding-keys.tsv`: 18 applied keys recorded for round 1 (flip, apply-time revalidation, untrusted-input boundary, `AskUserQuestion` in allowed-tools, default-pair-cap, mutation-eligibility, etc.).
- `.../plan-review/round-1/revise/revise.env`: `REVISE_STATUS=ok` with `REVISE_PLAN_HASH_BEFORE` != `REVISE_PLAN_HASH_AFTER` (round 1 rewrote `plan.txt`).
- `.../plan.txt` (final): contains "Do **not** auto-flip client and blocker", the untrusted-input section, `AskUserQuestion` in allowed-tools, and apply-time revalidation. The flip is gone.
- `.../plan-review/round-2/round-meta.json`: tally `ACCEPTED_COUNT=0, NEUTRAL_COUNT=18, REJECTED_COUNT=5`.
- `.../accepted-plan-findings.md`: empty. `.../rejected-findings.md`: 23 findings (round 2's), including `FINDING_1: In-flight flip writes Y blocked by X`.
- `python/plan_review.py`: `_read_applied_finding_keys` (line 1088), `_record_applied_finding_keys` (line 1103), `plan_review_continuation` uses the ledger only for continuation (lines 1156-1207).
- `skills/design/scripts/design-step3b-tail.sh` lines 107-111: cats `rejected-findings.md` unfiltered.
- `skills/design/SKILL.md` line 745: emits that body as `## Unimplemented Plan Review Suggestions`.

## Affected files

- `python/plan_review.py` — the `rejected-findings.md` writer (per-round tally) and `plan_review_continuation`; the existing `_read_applied_finding_keys` + `_finding_dedup_key` reconciliation should also gate the rejected-findings emit.
- `skills/design/scripts/design-step3b-tail.sh` — the `## Unimplemented Plan Review Suggestions` emit site (cats `rejected-findings.md` with no applied-key filter).
- `skills/design/SKILL.md` — Step 4 heading prose that promises "Unimplemented" semantics.
- Possibly `python/plan_review_panel.py` — for the secondary open question about which plan version round-2+ reviewers receive.

## Suggested fix(es)

- When building the rejected-findings body for Step 4, filter out (or annotate "addressed in an earlier round") any finding whose `_finding_dedup_key` is present in the cumulative applied ledger (`.step3-applied-finding-keys.tsv`). This reuses the existing #4808 keying, applying it to the reporting surface instead of only the continuation decision.
- Alternatively, accumulate a cumulative-aware rejected set the way `accepted-plan-findings-all.md` accumulates accepted findings, excluding applied keys, and emit that at Step 4.
- Investigate the secondary item: confirm round-2+ reviewers review the current revised `$DESIGN_TMPDIR/plan.txt` rather than a stale snapshot or scope-anchor only; if not, fix that to avoid re-litigating already-applied findings and the wasted round.

## Open questions

- Should already-applied-but-re-rejected findings be hidden entirely from "Unimplemented Plan Review Suggestions", or shown with an explicit "addressed in an earlier round" annotation for auditability?
- Do round-2+ reviewers actually review the revised `plan.txt`? Could not confirm from the published run log (round-2 per-reviewer prompts/outputs were not included). If they review a stale plan, that is a second, larger defect worth splitting into its own issue.

## Test plan
(no test plan section in plan-file)
