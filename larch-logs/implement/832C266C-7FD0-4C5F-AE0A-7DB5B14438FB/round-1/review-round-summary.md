# Review Round 1

- Mode: `diff`
- 1 accepted, 5 rejected (3 exonerated)

## Accepted Findings

### FINDING_5: Check (17) does not enforce continuation-banner vs `/larch:issue` ordering or tie `/larch:issue` to the banner line
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-test-pin-soundness-output.txt
- **Severity**: important
- **Concern**: Check (17) only requires the banner and `/larch:issue` anywhere strictly between the `### 5b` and `### 5c` headings, so the banner could sit above the `/larch:issue` instructions and still pass, encouraging the wrong execution order relative to written Step 5b flow. Separately, `grep -Fq '/larch:issue'` over the whole window does not tie `/larch:issue` to the continuation banner because Step 5b prose already mentions `/larch:issue` multiple times anywhere in that window, so the banner could drop the `/larch:issue` call-out while the check still passes—contradicting the failure message that the banner window must name `/larch:issue`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-test-pin-soundness-output.txt: Pin a single literal that appears only on the banner line (for example `grep -Fq 'Continue to Step 5c IMMEDIATELY.** The \`/larch:issue\` Skill tool' "$SKILL_MD"` after a line-number guard, or `grep -F` a full one-line substring joining the banner prefix and `` `/larch:issue` ``), or split the file at the banner line with `grep -n` and assert `/larch:issue` on that same line.


