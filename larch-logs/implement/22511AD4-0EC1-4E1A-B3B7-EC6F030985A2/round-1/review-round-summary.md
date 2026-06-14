# Review Round 1

- Mode: `diff`
- 1 accepted, 5 rejected (4 neutral)

## Accepted Findings

### FINDING_1: Harness pins retired Step 5d final-summary prose
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, dyn-summary-marker-output.txt
- **Severity**: important
- **Concern**: `scripts/test-render-cost-line-callsites.sh:74` still greps for the retired Step 5d string (`when \`$DESIGN_TMPDIR/final-summary.md\` or parsed \`FINAL_SUMMARY_PATH\` is non-empty after driver handoff`) while `skills/design/SKILL.md` now documents marker extraction after driver handoff. `bash scripts/test-render-cost-line-callsites.sh` / `make lint` fails even when plan-listed tests pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Update test-render-cost-line-callsites.sh to pin the new marker-extraction and file-fallback prose instead of the removed Step 5d string.
  - From codex-specialist-correctness-output.txt: Update the assertion to match the new marker-extraction plus fallback contract, or restore compatible prose in skills/design/SKILL.md.
  - From dyn-summary-marker-output.txt: Update line 74 to pin the new Step 5d marker-extraction + Read-fallback wording (or add a parallel grep for both contracts during transition).


