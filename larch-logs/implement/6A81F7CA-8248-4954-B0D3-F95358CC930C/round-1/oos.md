### FINDING_10: [OUT_OF_SCOPE] /tmp snapshot helper concurrent-run race (plan-accepted trade-off)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Global `/tmp` snapshot diff in `test-codex-implementer.sh` has a concurrent-run race window; parallel local runs or unrelated `/tmp/larch-codex-home-*` creation can cause spurious failures; plan accepted this trade-off.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add single-runner comment near snapshot helper
  - From cursor-specialist-correctness-output.txt: Isolate TMPDIR in launcher tests or accept single-runner CI constraint
  - From cursor-specialist-testing-output.txt: Add comment documenting no concurrent implementer launches; plan explicitly requested this
  - From cursor-specialist-plan-fidelity-output.txt: Keep plan contract or document CI isolation if flakiness appears


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_15: [OUT_OF_SCOPE] Legacy strip case duplicates lib-external unit strip tests
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Legacy strip case duplicates `lib-external` unit strip tests without unique failure modes; extra maintenance surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Defer unless integration wiring regression is a priority


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_19: [OUT_OF_SCOPE] OPENAI_API_KEY='' instead of unset subshell (functionally equivalent today)
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Login-mode cases use `OPENAI_API_KEY=''` instead of unset subshell; functionally equivalent today via length check in `external_codex_env_key_enabled`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Use unset subshell for plan consistency if desired


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_20: [OUT_OF_SCOPE] Mutation sanity checks not evidenced in session artifacts
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Plan-required mutation sanity and full harness matrix execution are not evidenced in diff/session artifacts; false-green assertions or failing harnesses could merge undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Run plan-required mutation sanity per harness before merge
  - From cursor-specialist-plan-fidelity-output.txt: Run and record remaining harness targets plus one assertion flip per file


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_25: [OUT_OF_SCOPE] multiline sq fixture documents stripper skips quoted bodies
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: New multiline sq fixture documents that stripper skips selectors inside triple-quoted literals; pre-existing stripper behavior, not introduced by this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Harden external_strip_codex_larch_env_provider if multiline embedding is in threat model


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_26: [OUT_OF_SCOPE] Pre-existing telemetry test never asserts CODEX_HOME cleanup
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Pre-existing codex-telemetry test never asserts `CODEX_HOME` cleanup; temp home survival on success path untested outside new failure case.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Add post-run removal assertion to codex-telemetry test
  - From cursor-specialist-plan-fidelity-output.txt: Add post-run removal assertion to codex-telemetry test


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_28: [OUT_OF_SCOPE] Env-key auth-prep failures swallowed in production
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Env-key auth-prep failures are swallowed in production; auth-prep breadcrumb unreachable on `OPENAI_API_KEY` path without prod change; correctly out of scope for this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Out of scope; branch correctly omits unreachable case


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### FINDING_29: [OUT_OF_SCOPE] Cleanup only on 4 and 4h is plan-scoped; 4f/4g omission matches plan
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Asserting cleanup only on tests 4 and 4h matches plan item 2; login paths 4f/4g omission is plan-intentional.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: No change required for plan fidelity

Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_9: [OUT_OF_SCOPE] Monolithic test-check-reviewers harness file
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-check-reviewers.sh` keeps growing with inline stubs; pre-existing structure not new to this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Consider modularizing in a separate refactor


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

