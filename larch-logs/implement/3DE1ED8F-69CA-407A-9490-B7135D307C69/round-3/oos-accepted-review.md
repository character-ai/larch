### OOS_3: [OUT_OF_SCOPE] Body substring heuristic for not-planned phrases can false-dock
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Body substring heuristic for not-planned phrases can false-dock unrelated discussion text. A closed issue body mentions "not planned for v2" while closed for another reason; fate section docks reviewer to 0.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Restrict body docking to close comments or structured close metadata when feasible.


### OOS_4: [OUT_OF_SCOPE] `degraded comment fetch` bucket may double-count with primary fate bucket
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Degraded comment fetch bucket double-counts alongside primary fate bucket for the same item. Bucket summary shows `degraded comment fetch: 5` and `docked combined-away: 5` for 5 items, confusing operators.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Either fold degraded into fate bucket reporting or document that degraded is additive telemetry only.


### OOS_5: [OUT_OF_SCOPE] Plan-listed rollup/join test fixtures not yet implemented
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-oos-reconciler-output.txt
- **Severity**: nit
- **Concern**: Many plan-listed rollup/join fixtures are not implemented in tests. Regressions in cap-rollup expansion, stable-id collision paths, main-agent bridge, and related join logic may slip without dedicated fixtures; the branch adds only a small subset of the plan's regression matrix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add the plan's rollup and collision tests when expanding coverage.
  - From dyn-oos-reconciler-output.txt: The main-agent and legacy-body bugs above are not locked by tests.


