## Goal
Implement issue #6027: [IMPLEMENTING] [BUG] Committed run logs omit rejected and neutral finding bodies.

## Implementation Plan
## Summary

Committed run logs preserve vote outcomes but not the text of rejected and neutral findings, so post-hoc adjudication cannot evaluate whether a rejection was sound. Several audited runs contain findings marked correctness=true by all three voters that landed rejected or neutral on plan-fidelity or pragmatism grounds, with no recoverable body in the committed log.

## Original report

From the 2026-07-02 post-merge audit. In the #5888 run, three in-scope findings were scored correctness=true by all 3 voters yet landed neutral or rejected; their bodies are not committed (reviewer outputs are referenced by session tmpdir paths that no longer exist). The same gap blocked adjudication in the #5969 run (one rejected finding scored partially-true/minor by 2 of 3 voters), the #5973 round-2 rejected and neutral findings, and the #5974 round-1 rejections. In some runs round-1/rejected-findings.md is empty despite a nonzero rejected count in round-meta.json.

## Reproduction scenario

Pick any recent run under larch-logs/implement/ with rejected findings in voting-tally.md and try to recover the rejected finding texts from the committed artifacts alone.

## Expected behavior

Redacted bodies of all voted findings (accepted, rejected, neutral) are committed with the round artifacts, so audits and mining skills (for example /rejected-analysis) can re-adjudicate later.

## Observed behavior

Only outcome pointers and vote metadata survive; rejected-findings.md is sometimes empty; finding texts referenced by tmpdir paths are unrecoverable after session cleanup.

## Root cause analysis

Uncertain. Either the round flush allowlist excludes the finding-body artifacts, or the tally writer records pointers into session-tmpdir files that are never staged for commit. Needs investigation in the round flush path and the tally/rejected-findings writers.

## Evidence

- larch-logs/implement/D5A9703D-6BF5-4F88-BB2B-D41DF184BBCF (#5888): voting-tally.md shows the true-but-rejected pattern; no bodies committed.
- larch-logs/implement/65BA514A-F205-46C1-B569-78F2B42AE88C (#5969), larch-logs/implement/B2573ABA-89B2-4C67-B8DA-7BAF5A37247F (#5973), larch-logs/implement/445D1144-4835-44B1-860C-183FA6E92CA1 (#5974): rejected or neutral findings unrecoverable from committed artifacts, as observed during the audit.

## Affected files

- python/larch/report/run_log_flush.py and the round-artifact staging allowlist.
- python/larch/review/review_tally.py and the rejected-findings writer.

## Suggested fix(es)

Commit redacted bodies for every voted finding into the round directory (extend rejected-findings.md to embed canonical finding text at vote time, through the existing redaction pipeline). If log size is a concern, commit bodies only for the adjudication-relevant subset: rejected findings with at least one true/valid vote, and all neutral findings.

## Open questions

- Was the omission an intentional run-log size bound? If so, is the subset proposal above an acceptable size/traceability trade?

## Test plan
(no test plan section in plan-file)
