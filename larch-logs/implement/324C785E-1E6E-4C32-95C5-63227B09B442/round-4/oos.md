### FINDING_16: [OUT_OF_SCOPE] Debate-phase Codex still uses pre-wired `launch-review.sh`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Debate-phase Codex in `skills/design/references/dialectic-execution.md:55-62` still uses `launch-review.sh`, which was already pre-wired for auth. Not introduced by this PR; debate paths were out of the six-site sweep. No change required for #3475 acceptance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=0 JUDGE_ERROR=2 Result=rejected

### FINDING_17: [OUT_OF_SCOPE] Generic `run-external-agent.sh` Codex path remains unwired for env-key auth
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, dyn-linter-fidelity-output.txt
- **Severity**: latent
- **Concern**: `scripts/run-external-agent.sh` remains a generic `"$@"` wrapper with no `external_prepare_codex_auth` wiring. Callers invoking Codex through `run-external-agent.sh` outside allowlisted launchers bypass `OPENAI_API_KEY` preference and shared auth helpers. Matches plan intent that the launcher layer owns auth, but the surface still does not enforce env-key auth itself.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Follow-up sweep per OOS issue; not required in this PR.
  - From cursor-specialist-security-output.txt: Out of scope; future sweep or linter extension
  - From dyn-linter-fidelity-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=0 JUDGE_ERROR=2 Result=rejected

### FINDING_18: [OUT_OF_SCOPE] No focused unit test for codex-exec outer-meta helper
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: There is no direct unit test for the codex-exec outer-meta helper in `scripts/test-lib-external-launcher-common.sh`. Metadata serialization bugs might only surface in full collector retry integration tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Optional: add focused cases to test-lib-external-launcher-common.sh per plan.


Vote tally: YES=0 NO=0 EXON=1 JUDGE_ERROR=2 Result=exonerated

### FINDING_19: [OUT_OF_SCOPE] `lint-codex-exec-auth.sh` scan roots omit hooks/agents/.github
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: The linter misses `hooks`, `agents`, and `.github` Codex exec sites. Future unwired exec in unscanned trees would not fail `make lint`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Extend scan roots or document explicit exclusion

---

**Subsumed without separate blocks** (positive validation or intentional scope, not actionable merge targets):

- FINDING_25: env-prefix skip regex behavior is correct and covered by tests
- FINDING_26: pragma suppression behavior is correct and covered by tests
- FINDING_27: prose/backtick `codex exec` mentions outside fenced shell blocks are intentionally out of scanner scope

Vote tally: YES=1 NO=0 EXON=0 JUDGE_ERROR=2 Result=rejected

