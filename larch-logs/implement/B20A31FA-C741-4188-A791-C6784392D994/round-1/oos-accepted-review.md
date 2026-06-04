### FINDING_10: [OUT_OF_SCOPE] Missing lib strip failure and post-table fixtures
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-toml-strip-output.txt
- **Severity**: important
- **Concern**: `scripts/test-lib-external-launcher-common.sh` does not cover strip failure, no-symlink fail-closed behavior, post-table selector retention, multiline string corruption, or related unsafe rewrite cases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-toml-strip-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_12: [OUT_OF_SCOPE] launch-review docs stale after auth behavior change
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `scripts/launch-review.md` does not describe the new Codex auth behavior, leaving operator-facing documentation stale.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_15: [OUT_OF_SCOPE] Direct codex helpers remain outside shared auth surface
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-codex-auth-flow-output.txt
- **Severity**: latent
- **Concern**: `/research` and other direct `codex exec` helpers do not use the new shared auth helper, so `OPENAI_API_KEY` preference may not apply uniformly outside the scoped launcher surfaces.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, dyn-codex-auth-flow-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


### FINDING_16: [OUT_OF_SCOPE] Redactor lacks explicit OPENAI_API_KEY value scrubbing
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `scripts/redact-secrets.sh` has `sk-*` patterns but no explicit `OPENAI_API_KEY=` value scrubber, so unusual key formats in vendor error output might survive.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


### FINDING_19: [OUT_OF_SCOPE] review-and-fix omits Codex model/effort argv parity
- **Reviewer(s)**: dyn-codex-auth-flow-output.txt, dyn-bash-argv-output.txt
- **Severity**: important
- **Concern**: `skills/review-and-fix/scripts/review-and-fix.sh` builds trust/auth args but does not include `agent-model-args.sh --tool codex --with-effort`, unlike the other launcher/probe surfaces.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-codex-auth-flow-output.txt, dyn-bash-argv-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_23: [OUT_OF_SCOPE] Single-quoted legacy env_key forms are not stripped
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-toml-strip-output.txt
- **Severity**: latent
- **Concern**: Legacy larch selector lines using single-quoted or non-standard forms can survive the login strip path if such configs exist.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-toml-strip-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_24: [OUT_OF_SCOPE] Branch-scope observation only
- **Reviewer(s)**: dyn-bash-argv-output.txt
- **Severity**: nit
- **Concern**: Reviewer noted which commits were on the branch and that the review targeted the Codex auth argv work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-argv-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected


### FINDING_25: [OUT_OF_SCOPE] Shared helper argv construction appears to match plan
- **Reviewer(s)**: dyn-bash-argv-output.txt
- **Severity**: nit
- **Concern**: Reviewer observed that shared auth argv construction and ordering in the main implement/review/CI launchers match the plan and existing tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-argv-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected


### FINDING_26: [OUT_OF_SCOPE] Pre-existing line-based instruction strip shares TOML blind spot
- **Reviewer(s)**: dyn-toml-strip-output.txt
- **Severity**: latent
- **Concern**: Existing instruction-stripping code in `launch-review.sh` and `launch-codex-implement.sh` shares the multiline-string blind spot, though the new helper broadens the exposure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-toml-strip-output.txt: Address the concern above.

Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_9: [OUT_OF_SCOPE] launch-review auth-prep failure contract differs from other launchers
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, dyn-bash-argv-output.txt
- **Severity**: latent
- **Concern**: `scripts/launch-review.sh` exits non-zero on Codex auth-prep failure while implement/CI paths emit launcher KVs and exit 0, which may confuse collectors or retry logic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, dyn-bash-argv-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


