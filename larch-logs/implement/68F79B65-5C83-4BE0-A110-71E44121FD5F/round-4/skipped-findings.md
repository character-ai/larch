### FINDING_3: `--voter` column placement uses basename/tool heuristics, not dispatch order
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `--voter` column placement uses basename/tool heuristics rather than argv or panel dispatch order (`vN_tool` comes from SLOT label). Manual or partial-panel invocations with mismatched `SLOT:PATH` pairs can record ratings under the wrong `vN` column while `vN_tool` shows the declared tool, corrupting analytics (e.g. sole slot-2 judge landing in `v1`). Plan wording on dispatch order vs tally canonical-slot authority is also inconsistent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.



