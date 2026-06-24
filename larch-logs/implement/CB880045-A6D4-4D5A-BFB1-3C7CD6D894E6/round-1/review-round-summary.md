# Review Round 1

- Mode: `diff`
- 4 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Marker-first Read fallback can double-emit on /design Step 5c
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Committed `skills/shared/final-summary-emit.md` step 5 gates Read fallback on caller policy only, not on marker extraction failure. When `/design` Step 5c notification stdout contains valid `LARCH_FINAL_SUMMARY` markers and `final-summary.md` is non-empty, an orchestrator can emit the marker body and then Read-emit the file again, duplicating the final summary in chat.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Commit the working-tree step 5 guard: Only when steps 1–2 yield no valid marker body and Read fallback policy is allowed.
  - From cursor-specialist-edge-cases-output.txt: Commit the unstaged step-5 guard and matching harness assertion at scripts/test-render-cost-line-callsites.sh:90.
  - From cursor-specialist-testing-output.txt: Restore Only when steps 1-2 yield no valid marker body and the caller Read fallback policy is allowed before Read fallback; commit the matching harness pin.


### FINDING_2: Duplicate Step 17 inline emit prose conflicts with shared profile
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Committed `skills/implement/SKILL.md` binds the shared marker-first profile at Step 17 (lines 923+) but re-adds legacy inline “extracted marker body” prose on the following line. An orchestrator may follow the duplicate line instead of the shared profile, bypassing forbidden Read fallback and sidecar policy for Step 17/18b emission.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Delete line 925; keep retired-prose harness grep; commit with the change set.
  - From cursor-specialist-edge-cases-output.txt: Commit the unstaged removal of the duplicate line; keep ONLY the shared-profile binding in NEVER #17 and Step 17.
  - From cursor-specialist-testing-output.txt: Delete line 925; add extracted marker body defined in Step 17 to retired_prose negative grep.


### FINDING_3: Harness pins policy-only Read fallback, not marker-absence guard
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `scripts/test-render-cost-line-callsites.sh` at line 90 pins only the policy-only Read-fallback sentence. A regression that removes the step-5 marker-failure guard would still pass `make test-render-cost-line-callsites` on committed HEAD.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Commit the working-tree grep for steps 1–2 yield no valid marker body and caller policy allowed.
  - From cursor-specialist-testing-output.txt: Update the grep needle to require steps 1-2 yield no valid marker body in the shared anchor step-5 sentence.


### FINDING_5: Positional runner call breaks Step 5 accepted-findings coder path
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: blocking
- **Concern**: `apply_findings_with_coder` at `python/review_and_fix.py:2193` still calls `runner(round_dir, prompt_body, tool_log)` positionally, but `_run_coder_cursor` and `_run_coder_codex` at lines 2022 and 2075 use keyword-only signatures. Any Step 5 path with accepted findings reaches this call and raises `TypeError` before Cursor can run or Codex can fall through.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Call the runner with keywords: `runner(round_dir=round_dir, prompt_body=prompt_body, tool_log=tool_log)`, and keep the monkeypatched tests keyword-only so this path is covered.


