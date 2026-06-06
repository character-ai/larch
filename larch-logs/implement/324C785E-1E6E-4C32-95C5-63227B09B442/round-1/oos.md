### FINDING_27: [OUT_OF_SCOPE] `scripts/run-external-agent.sh` remains generic codex dispatcher without shared auth
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-linter-bypass-output.txt
- **Severity**: latent
- **Concern**: Generic external-agent wrapper still dispatches raw `codex exec` without env-key auth wiring; auth remains caller responsibility and is outside this PR’s six swept surfaces. Future callers bypassing launchers miss `OPENAI_API_KEY` preference unless caught by linter patterns.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Follow-up sweep if centralizing auth at wrapper is desired.
  - From cursor-specialist-correctness-output.txt: Follow-up sweep per OOS issue #3475.
  - From cursor-specialist-testing-output.txt: Follow-up sweep per OOS; out of this PR scope.
  - From cursor-specialist-security-output.txt: No change required unless consolidating all codex dispatch through one launcher (explicitly out of scope).
  - From cursor-specialist-edge-cases-output.txt: Follow-up sweep per original OOS issue.
  - From dyn-linter-bypass-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_28: [OUT_OF_SCOPE] Auth setup duplicated across launch-codex-exec, launch-codex-ci, run-negotiation-round
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Auth setup is intentionally duplicated per plan across multiple launchers, increasing long-term parity maintenance burden.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Consider shared prepare-codex-home helper in a future refactor.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_29: [OUT_OF_SCOPE] Negotiation auth harness gap noted as follow-up
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Negotiation auth wiring lacks planned env-key/login/cleanup harness coverage as an explicit out-of-scope follow-up distinct from in-scope plan acceptance on the same harness file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add planned auth-mode and temp `CODEX_HOME` cleanup assertions.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_30: [OUT_OF_SCOPE] No structural pin for launch-codex-exec fences in research references
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: No research-specific structural pin for `launch-codex-exec` fences; fence could regress to raw `codex exec` without research-specific harness failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Rely on lint-codex-exec-auth or add research-structure pin.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_31: [OUT_OF_SCOPE] `collect-agent-results.md` omits new `jq` dependency for codex-exec outer retry
- **Reviewer(s)**: dyn-jq-retry-absent-output.txt
- **Severity**: latent
- **Concern**: Contract still says outer-launcher branch “does not deserialize `CMD_JSON`” and implies `jq` is only needed on inner `CMD_JSON` path, but `OUTER_LAUNCHER_KIND=codex-exec` now hard-depends on `jq` for `OUTER_LAUNCHER_ADD_DIRS_JSON`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-jq-retry-absent-output.txt: Address the concern above.

Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

