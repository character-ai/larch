### FINDING_3: Step 1d sprawl split-path still routes to Gate A
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-routing-completeness-output.txt
- **Severity**: important
- **Concern**: SKILL.md’s Step 2b.5 split-path return still routes Step 1d sprawl to Step 1e Gate A, while decompose-panel.md routes the same path to Step 1d.7 outline approval. This can bypass the new first-time outline gate or land on the wrong prompt surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-routing-completeness-output.txt: Address the concern above.



