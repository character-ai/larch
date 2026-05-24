### FINDING_1: Step 3 drops explicit `run-params.json` read; harness and `review_budget` prose merged
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-bash-portability-output.txt, dyn-skill-md-continuity-output.txt
- **Severity**: important
- **Concern**: Step 3 text merges the hermetic harness pointer with the `review_budget` / valid-values / `quick_mode` fallback paragraph and no longer leads with an explicit instruction to read `review_budget` from `$DESIGN_TMPDIR/run-params.json` before the **If review_budget=quick** / **If review_budget=full** branches. That weakens the mechanical contract (and can contradict deferral text elsewhere): orchestrators may infer `review_budget` from context or misread the harness sentence as the source of truth, mis-routing quick vs full. Relatedly, harness guidance and normative `run-params.json` rules appear in one paragraph, increasing the risk of future edits dropping normative sentences.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-bash-portability-output.txt, dyn-skill-md-continuity-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Split into two paragraphs: harness pointer vs run-params review_budget rules


### FINDING_2: Issue acceptance vs documented chat order (breadcrumb, timing ledger, plan preview)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-portability-output.txt
- **Severity**: important
- **Concern**: Acceptance / issue-level text still treats the plan preview as immediately after the Step 3 breadcrumb, while SKILL and `docs/configuration-and-permissions.md` describe timing-ledger output before the preview. Manual QA, log audits, or merge checklists keyed only on breadcrumb adjacency can false-fail even when behavior matches the documented ordering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-bash-portability-output.txt: Address the concern above.


### FINDING_5: Written plan vs branch surface (topology, new script, tests, Makefile, file-count claims)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Plan / documentation impact claims (e.g., topology unchanged, bounded file set, no new scripts) diverge from the branch, which adds `emit-design-plan-preview.sh`, test and Makefile wiring, `skills/shared/topology.tsv` (and related rules). That weakens plan-to-implementation traceability and can mislead release notes or review gates that assumed a smaller declared file set.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_7: `touch` on `.step3-entry-plan-printed` under `set -e` can abort the script
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `touch` on `.step3-entry-plan-printed` runs under `set -e` and can fail the fenced block on read-only tmpdir or full disk after emitting the preview; empty-plan paths may re-spam warnings if the marker never succeeds. Prefer best-effort `touch` or failure handling that does not fail the whole script.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_8: Regression harness under-covers Gate C and threshold normalization paths
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `test-emit-design-plan-preview.sh` focuses on Step 3 paths but does not adequately cover Gate C (e.g., large-plan summary, 4b-style warnings, invalid-threshold / `abc` / `0` threshold silent fallback). Regressions in the Gate C branch or threshold normalization could ship without CI signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


