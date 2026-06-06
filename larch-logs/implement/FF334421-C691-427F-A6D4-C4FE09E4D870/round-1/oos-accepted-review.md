### FINDING_1: [OUT_OF_SCOPE] Branch bundles unrelated design/run-log work with ship-driver flip
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-ship-state-output.txt, dyn-bash32-output.txt
- **Severity**: important
- **Concern**: The branch combines the Python ship-driver default flip with substantial unrelated `/design` scope-anchor/run-log work, increasing review noise, regression attribution risk, and revert/bisect complexity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Split PRs or rebase so the ship-driver flip lands alone (or with minimal deps).
  - From cursor-specialist-testing-output.txt: Split PRs or run full make lint/harness shards and document coupling.
  - From cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-ship-state-output.txt, dyn-bash32-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


### FINDING_10: [OUT_OF_SCOPE] Default Python flip ships before soak/security blockers are resolved
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-ship-state-output.txt, dyn-plan-voting-output.txt, dyn-contract-drift-output.txt
- **Severity**: important
- **Concern**: The default path now routes unset `LARCH_SHIP_PR_IMPL` runs through less-soaked Python paths with known blockers, while `SECURITY.md` removes/softens prior pending-review language.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Track blockers; document opt-out LARCH_SHIP_PR_IMPL=bash prominently.
  - From cursor-specialist-security-output.txt: Gate default flip on listed blockers or complete python/ship.py and python/finalize.py review and document residual risks instead of claiming unchanged properties.
  - From cursor-specialist-edge-cases-output.txt: Document escape hatch; close blockers or add env-based soak gate.
  - From dyn-ship-state-output.txt, dyn-plan-voting-output.txt, dyn-contract-drift-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


### FINDING_29: [OUT_OF_SCOPE] `stall-recovery-report.sh` finalize consult was pre-existing
- **Reviewer(s)**: dyn-ship-state-output.txt, dyn-bash32-output.txt
- **Severity**: nit
- **Concern**: Reviewers noted that `stall-recovery-report.sh` already consulted `finalize-state.sh`; this branch mostly extended docs/tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ship-state-output.txt, dyn-bash32-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected


### FINDING_30: [OUT_OF_SCOPE] Bash 3.2 portability appears preserved
- **Reviewer(s)**: dyn-bash32-output.txt
- **Severity**: nit
- **Concern**: New shell test windows use Bash 3.2-safe constructs and no Bash 4-only features were identified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash32-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected


### FINDING_31: [OUT_OF_SCOPE] Prompt-safety hardening positives
- **Reviewer(s)**: dyn-prompt-safety-output.txt
- **Severity**: nit
- **Concern**: Reviewer called out positive hardening in scout/subprocess prompt rendering, delimiter-breakout harnesses, and plan-mode aggregation filtering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-safety-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected


### FINDING_32: [OUT_OF_SCOPE] Pre-existing raw path printing in prompt renderers
- **Reviewer(s)**: dyn-prompt-safety-output.txt
- **Severity**: nit
- **Concern**: Raw `PLAN_FILE` / `BALLOT_FILE` path printing into prompts is pre-existing and unchanged by the branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-safety-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected


### FINDING_33: [OUT_OF_SCOPE] Commit-list observations
- **Reviewer(s)**: dyn-prompt-safety-output.txt
- **Severity**: nit
- **Concern**: Reviewer listed branch commits for context rather than raising a behavioral defect.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-safety-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected


