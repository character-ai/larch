## Goal
Implement issue #6028: [IMPLEMENTING] [BUG] OOS-dropped real findings have no filing path; 0 OOS filed across 11 audited runs.

## Implementation Plan
## Summary

All 11 implement runs audited on 2026-07-02 report "OOS filed: 0" while their round-1/oos-dropped-before-vote.md files contain findings the audit independently confirmed as real. Dropped-before-vote OOS items have no path to an issue: accepted OOS in /review description mode has a manual follow-up surface, and /rejected-analysis mines rejected findings, but pre-vote drops are covered by neither. Real gaps therefore recur until a manual audit finds them.

## Original report

From the 2026-07-02 post-merge audit of the last 11 closed issues. Examples of dropped-but-real items from those runs, all now filed as separate issues by this batch: the closeout-time pin gap (from the #5969 run, OOS_1), the collector cursor CMD_JSON lane (from the #5972 run, OOS_3), the claude-ci retry gaps (from the #5971 run, OOS_3/OOS_4), and the SECURITY.md staleness flagged at severity "important" (from the #5982 run, OOS_2).

## Reproduction scenario

Read run-statistics.md ("OOS filed: 0") and round-1/oos-dropped-before-vote.md in the cited run-log directories; check the issue tracker for any issue tracking the dropped items (none existed before this batch).

## Expected behavior

Genuinely real dropped-OOS items reach a filing surface: an auto-file step, a closeout candidate list for the operator, or coverage by an existing mining skill.

## Observed behavior

No surface exists for the dropped-before-vote class. The items live only in the committed oos-dropped-before-vote.md files, which nothing consumes.

## Root cause analysis

Inference: the pre-vote OOS gate was added to cut voting cost, and the OOS filing pipeline remained attached only to post-vote outcomes, leaving the pre-vote drop class untracked by design accident rather than decision.

## Evidence

- run-statistics.md OOS counters are zero in all 11 audited runs (directories listed in the sibling audit issues).
- round-1/oos-dropped-before-vote.md contents in larch-logs/implement/65BA514A-F205-46C1-B569-78F2B42AE88C, 7623E215-D6C5-4123-8334-D1EAB4B29278, 9DABFAEB-4BE3-4847-B85B-9FB630E959C4, and 454633C3-5D3B-4678-818F-56D3A3C26D6D contain the confirmed-real examples above.

## Affected files

- The /implement closeout or final-summary flow (surface candidates to the operator), or
- skills/rejected-analysis (extend mining scope to oos-dropped-before-vote.md).

## Suggested fix(es)

- Emit a bounded "dropped OOS candidates" section in the final summary or closeout output with one-line rationales, suitable for feeding /issue batch mode.
- Or extend /rejected-analysis to mine oos-dropped-before-vote.md in addition to rejected findings.

## Open questions

- Is zero-OOS-filed the intended cost policy, with periodic audits as the recovery path? If so, document that in docs/run-logs.md and close this issue as working-as-intended.

## Test plan
(no test plan section in plan-file)
