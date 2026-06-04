### FINDING_20: [OUT_OF_SCOPE] research and direct codex exec helpers remain on old auth model
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-auth-secrets-output.txt, dyn-launcher-parity-output.txt
- **Severity**: latent
- **Concern**: `/research`, negotiation, lint-fix, and other direct `codex exec` paths are not wired through the shared env-key auth helper. Reviewers marked this as out-of-scope or explicitly documented for this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, dyn-auth-secrets-output.txt, dyn-launcher-parity-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_21: [OUT_OF_SCOPE] core env-key design positive observation
- **Reviewer(s)**: dyn-auth-secrets-output.txt
- **Severity**: nit
- **Concern**: the reviewer observed that the core env-key design avoids value expansion, passes only fixed `-c` tokens naming `OPENAI_API_KEY`, and avoids writing provider auth or symlinking `auth.json` in env-key mode.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-auth-secrets-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected


### FINDING_22: [OUT_OF_SCOPE] login fallback still symlinks plaintext auth.json
- **Reviewer(s)**: dyn-auth-secrets-output.txt
- **Severity**: latent
- **Concern**: when `OPENAI_API_KEY` is unset or empty, login fallback still symlinks `~/.codex/auth.json`, which may contain plaintext credentials. Reviewer marked this as pre-existing and unchanged.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-auth-secrets-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_23: [OUT_OF_SCOPE] SECURITY.md Cursor argv text is stale
- **Reviewer(s)**: dyn-auth-secrets-output.txt
- **Severity**: nit
- **Concern**: `SECURITY.md` still describes Cursor `--api-key` argv persistence above the new Codex env-key section; reviewer marked this as stale relative to a prior issue and not introduced by this Codex change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-auth-secrets-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_27: [OUT_OF_SCOPE] stripper requires writable config
- **Reviewer(s)**: dyn-toml-stripper-output.txt
- **Severity**: latent
- **Concern**: the strip helper requires write permission on `config.toml`; reviewers marked this as unlikely in production because launchers create writable temp homes, and failure would abort auth prep.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-toml-stripper-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected


### FINDING_28: [OUT_OF_SCOPE] stripper is intentionally not a full TOML parser
- **Reviewer(s)**: dyn-toml-stripper-output.txt
- **Severity**: latent
- **Concern**: residual TOML edge cases such as inline tables, dotted keys, or non-larch provider `env_key` entries remain because the helper is not a full parser. Reviewer marked this as outside the stated larch-owned artifact contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-toml-stripper-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected


### FINDING_31: [OUT_OF_SCOPE] probe temp-home lifecycle looks consistent but unasserted
- **Reviewer(s)**: dyn-probe-cache-output.txt
- **Severity**: nit
- **Concern**: reviewer observed the probe temp `CODEX_HOME` cleanup paths and EXIT trap look consistent, while noting the branch does not add harness assertions that probe-home directories are gone after each path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-probe-cache-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_32: [OUT_OF_SCOPE] env-key cache semantics are stricter than docs prose
- **Reviewer(s)**: dyn-probe-cache-output.txt
- **Severity**: nit
- **Concern**: env-key mode bypasses all stamps, including fresh `true`, which matches fail-loud key-rotation intent but is broader than `scripts/check-reviewers.md` prose saying cached `false` is treated as a miss.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-probe-cache-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


### FINDING_33: [OUT_OF_SCOPE] legacy probe stamps cause one-time extra probe
- **Reviewer(s)**: dyn-probe-cache-output.txt
- **Severity**: nit
- **Concern**: pre-branch `larch-codex-present-${USER}.stamp` files are no longer read; reviewer classified this as a one-time extra probe after upgrade, not incorrect availability signaling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-probe-cache-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected


### FINDING_35: [OUT_OF_SCOPE] pre-existing Codex-to-Cursor waterfall hid failures
- **Reviewer(s)**: dyn-fallback-observability-output.txt
- **Severity**: latent
- **Concern**: Codex-to-Cursor fallback without env-key mode already hid Codex failure from stdout when Cursor succeeded; reviewer marked this broader waterfall-observability issue as pre-existing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-fallback-observability-output.txt: Address the concern above.

Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_9: [OUT_OF_SCOPE] Step 5 Codex dispatch lacks model-args parity
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-launcher-parity-output.txt
- **Severity**: nit
- **Concern**: `skills/review-and-fix/scripts/review-and-fix.sh` passes trusted-project and auth overrides but does not call `agent-model-args.sh --tool codex`, unlike other covered Codex paths. Reviewers marked this as pre-existing/out-of-scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, dyn-launcher-parity-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


