### OOS_1: [OUT_OF_SCOPE] Dual BACKTICKED list drift risk
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `.github/workflows/ci.yaml:419-429` and `python/voting.py:45-55` duplicate `BACKTICKED_FILES` and `BACKTICKED_FOCUS_FILES`; both were updated in this PR, but there is no mechanical guard against future drift if only one side changes. Pre-existing dual-source pattern, not introduced by this deletion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] CI-fix agents lost topology troubleshooting hints
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `python/ci_agentic_fix.py` — CI-fix agents no longer receive topology.tsv troubleshooting hints that lived in the deleted `ci-fix-failure-patterns.md`. The plan explicitly forbids re-wiring CI-fix grounding; constraints were moved to the path-triggered topology rule for editors only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] topology-generation rule omits `--check` variant
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `.claude/rules/topology-generation.md:29-31` documents full `generate topology-docs` but not the `--check` variant that the deleted CI-fix doc mentioned. Plan edge case says not to duplicate the deleted doc wholesale; `python/rendering.py` still enforces validation at generation time.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
