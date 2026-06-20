### [Plan Review] FINDING_3

### FINDING_3: No-ledger early return bypasses `--report-framing`
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan lists framing for filtered rejected bodies but not the `if not applied: print(text)` branch at python/plan_review.py:1243-1245. Edge cases require ledger-missing output to still be framed when `--report-framing` is set. Without an explicit wrap on that branch, wrapper `--report-framing` can emit bare rejected blocks (no considered-not-adopted heading/annotation) and partially reintroduce #4884 misleading output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: In `emit_rejected_findings`, apply the same `--report-framing` wrapper to every non-empty stdout path, including the `not applied` early return; add a test mirroring `test_emit_rejected_without_ledger_emits_verbatim` with `--report-framing` asserting heading/annotation presence.


### [Plan Review] FINDING_4

### FINDING_4: Shell CLI-failure fallback bypasses report framing
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan requires the shell fallback to print heading/annotation before `cat rejected-findings.md`, but design-step3b-tail.sh today only cats on non-zero exit from `emit-rejected --report-framing`. If framing lives only inside Python `--report-framing`, any CLI failure bypasses reframing and can surface stale unimplemented semantics under the markers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: In the `if ! ... emit-rejected --report-framing` branch, print the same heading/annotation strings before `cat`, or call a small shared framing helper; add a wrapper/contract test that non-zero `emit-rejected` still yields framed operator output.
```


