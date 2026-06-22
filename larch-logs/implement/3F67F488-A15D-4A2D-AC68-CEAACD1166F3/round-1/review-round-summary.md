# Review Round 1

- Mode: `diff`
- 2 accepted, 5 rejected (4 neutral)

## Accepted Findings

### FINDING_6: agnix-fix may still flag adjacent bash fences on first-run lint
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The plan names agnix-fix for first-run remediation, but the diff adds no suppression there. Adjacent bash fences at `.claude/skills/agnix-fix/SKILL.md:52-68` and `72-97` appear separated only by a one-line breadcrumb gap. `make lint` / pre-commit `lint-consecutive-bash` can exit 1 despite other scoped files being remediated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Run python3 python/cli.py lint consecutive-bash; if flagged, add a justified suppression using the correct placement form for that fence shape.


### FINDING_7: WRONG/CORRECT pair carve-out ignores inter-fence gap text
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-dyn-fence-parser-output.txt
- **Severity**: important
- **Concern**: `_is_wrong_correct_pair` builds search text from `preceding_context`, fence `info`, and fence `body` only; it never includes `gap_lines`. When `WRONG:` / `CORRECT:` labels sit in the inter-fence gap, `_gap_is_adjacent` may still treat the gap as short breadcrumb prose, but the WRONG/CORRECT exemption will not fire, producing false positives on instructional pairs the plan explicitly exempts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Include gap_lines in _is_wrong_correct_pair and add a regression test.
  - From dyn-dyn-fence-parser-output.txt: Include `gap_lines` in the WRONG/CORRECT scan (same as `_combined_pair_text` does for other carve-outs), or call `_is_wrong_correct_pair(first, second, gap_lines)` and search the full combined span; add a pytest case with labels only in the gap.


