### FINDING_10: [OUT_OF_SCOPE] Step 5 auth harness lacks required failure/fallback coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-auth-flow-output.txt
- **Severity**: important
- **Concern**: `test-review-and-fix.sh` does not fully cover login fallback, auth-prep failure, env-key dispatch failure breadcrumbs, and sentinel leak assertions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-auth-flow-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_11: [OUT_OF_SCOPE] Codex probe harness misses plan acceptance cases
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-lifecycle-output.txt, dyn-probe-cache-output.txt
- **Severity**: important
- **Concern**: `test-check-reviewers.sh` lacks coverage for trust argv, env-key no-auth behavior, sentinel leaks, legacy strip behavior, and probe temp-home cleanup after retry/failure paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-lifecycle-output.txt, dyn-probe-cache-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_25: [OUT_OF_SCOPE] Cursor/run-external-agent metadata argv persistence
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-secret-surface-output.txt
- **Severity**: latent
- **Concern**: `run-external-agent.sh` / Cursor metadata can persist full child argv in `.meta`/`CMD_JSON`; this is pre-existing or documented, but remains a security surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, dyn-secret-surface-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_26: [OUT_OF_SCOPE] TOML CRLF/table parsing edge cases
- **Reviewer(s)**: dyn-toml-strip-output.txt
- **Severity**: nit
- **Concern**: Table-header detection is not full TOML parsing and may miss CRLF-terminated or similar Windows-saved config edge cases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-toml-strip-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_27: [OUT_OF_SCOPE] Strip docs say top-level but implementation strips globally
- **Reviewer(s)**: dyn-toml-strip-output.txt
- **Severity**: latent
- **Concern**: Helper docs describe removing top-level legacy keys, while implementation strips matching lines globally, including provider tables.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-toml-strip-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_28: [OUT_OF_SCOPE] CI model-args tempfile can leak if temp home creation fails
- **Reviewer(s)**: dyn-bash-lifecycle-output.txt
- **Severity**: latent
- **Concern**: `launch-codex-ci.sh` creates `MODEL_ARGS_TMP` before installing the cleanup trap, so a failure before trap setup can leak the tempfile.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-lifecycle-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


### FINDING_29: [OUT_OF_SCOPE] Reverse auth-mode stamp transition lacks harness coverage
- **Reviewer(s)**: dyn-probe-cache-output.txt
- **Severity**: nit
- **Concern**: The probe harness lacks a test for clearing `OPENAI_API_KEY` after env-key success while a stale login-false stamp remains.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-probe-cache-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


### FINDING_30: [OUT_OF_SCOPE] SECURITY.md older paragraph omits env-key precedence
- **Reviewer(s)**: dyn-secret-surface-output.txt
- **Severity**: nit
- **Concern**: A newer `SECURITY.md` section documents env-key auth, but an older external delegation paragraph still describes only `auth.json` symlink behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-secret-surface-output.txt: Address the concern above.

Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


### FINDING_9: [OUT_OF_SCOPE] Direct Codex lanes are not wired to shared env-key auth
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, dyn-auth-flow-output.txt
- **Severity**: latent
- **Concern**: Uncovered direct `codex exec` paths such as lint-fix, negotiation, and `/research` can still prefer login auth even when `OPENAI_API_KEY` is set.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, dyn-auth-flow-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


