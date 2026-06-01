### FINDING_14: [OUT_OF_SCOPE] Pre-Step-0 SKILL prose uses CLAUDE_PLUGIN_ROOT without fence rehydration
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Pre-Step-0 prose at `skills/implement/SKILL.md:12,91` uses `CLAUDE_PLUGIN_ROOT` without fence rehydration; pre-existing, relies on plugin env at session start. No change required for this PR.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=1 JUDGE_ERROR=0 Result=exonerated


### FINDING_15: [OUT_OF_SCOPE] Invariant C fence matcher lacks whitespace tolerance for indented bash
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Invariant C in `scripts/test-implement-timing-rehydration.sh` only matches `^```bash$` openers, not indented fence markers. Indented Preflight/helper snippets using `CLAUDE_PLUGIN_ROOT` are not checked for rehydration adjacency (pre-existing).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=1 JUDGE_ERROR=0 Result=exonerated


