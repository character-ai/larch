### FINDING_17: [OUT_OF_SCOPE] Login fallback may symlink auth.json containing plaintext keys
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Login fallback symlinks `~/.codex/auth.json`, which may contain plaintext keys if created with `codex login --with-api-key`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_20: [OUT_OF_SCOPE] Consecutive multiline-token handling appears covered
- **Reviewer(s)**: dyn-toml-strip-awk-output.txt
- **Severity**: nit
- **Concern**: The scout’s consecutive-token question appears satisfied; odd/even occurrence counting works for same-line open/close pairs and whole-line comment fixtures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-toml-strip-awk-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_21: [OUT_OF_SCOPE] Larch provider table skipping recovery appears covered
- **Reviewer(s)**: dyn-toml-strip-awk-output.txt
- **Severity**: nit
- **Concern**: Single- and double-bracket larch provider headers are both matched, and existing malformed-table fixtures exercise recovery to the next non-larch header.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-toml-strip-awk-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_22: [OUT_OF_SCOPE] Existing comment fixture does not cover inline comment triples
- **Reviewer(s)**: dyn-toml-strip-awk-output.txt
- **Severity**: nit
- **Concern**: The current `# comment with """` fixture only validates whole-line comments, not inline comment text after assignments.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-toml-strip-awk-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_24: [OUT_OF_SCOPE] Env-key enabled Bash pattern is xtrace-safe
- **Reviewer(s)**: dyn-secret-eval-xtrace-output.txt
- **Severity**: nit
- **Concern**: The `${OPENAI_API_KEY+x}` / `${#OPENAI_API_KEY}` pattern is appropriate for Bash 3.2 and traces only presence/length, not the secret value.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-secret-eval-xtrace-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_25: [OUT_OF_SCOPE] Auth config eval array-name validation is tight enough
- **Reviewer(s)**: dyn-secret-eval-xtrace-output.txt
- **Severity**: nit
- **Concern**: Current array-name validation blocks obvious eval injection for static call sites, though eval remains a future footgun for dynamic callers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-secret-eval-xtrace-output.txt: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_26: [OUT_OF_SCOPE] CMD_JSON records variable name, not secret value
- **Reviewer(s)**: dyn-secret-eval-xtrace-output.txt
- **Severity**: nit
- **Concern**: Env-key launches persist `-c` overrides including the `OPENAI_API_KEY` variable name in session-private metadata, but not the key value.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-secret-eval-xtrace-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_27: [OUT_OF_SCOPE] Env auth still exposes key through inherited environment
- **Reviewer(s)**: dyn-secret-eval-xtrace-output.txt
- **Severity**: nit
- **Concern**: Env-key mode avoids putting the secret on argv, but the child necessarily inherits `OPENAI_API_KEY`, with inherent same-user environment visibility.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-secret-eval-xtrace-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### FINDING_29: [OUT_OF_SCOPE] Implement launcher trap ordering appears satisfied
- **Reviewer(s)**: dyn-temp-home-lifecycle-output.txt
- **Severity**: nit
- **Concern**: `launch-codex-implement.sh` initializes cleanup state and installs the EXIT trap before auth prep, so auth-prep failure still removes `CODEX_HOME_DIR`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-temp-home-lifecycle-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_30: [OUT_OF_SCOPE] Review-and-fix temp-home double cleanup is redundant but safe
- **Reviewer(s)**: dyn-temp-home-lifecycle-output.txt
- **Severity**: nit
- **Concern**: `review-and-fix.sh` avoids empty-path registration on `mktemp` failure, removes created Codex homes inline, and then re-removes them via EXIT cleanup; this is redundant but safe.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-temp-home-lifecycle-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_31: [OUT_OF_SCOPE] Probe dir registry double cleanup is idempotent after normal return
- **Reviewer(s)**: dyn-temp-home-lifecycle-output.txt
- **Severity**: nit
- **Concern**: After normal probe completion, `PROBE_DIRS` may contain already-removed paths, but the EXIT cleanup’s second `rm -rf` is idempotent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-temp-home-lifecycle-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_32: [OUT_OF_SCOPE] Launch-review trap registration pattern appears sound
- **Reviewer(s)**: dyn-temp-home-lifecycle-output.txt
- **Severity**: nit
- **Concern**: `launch-review.sh` initializes `CODEX_HOME_DIR` before registering the EXIT trap and creates the temp home later, matching the implement launcher pattern.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-temp-home-lifecycle-output.txt: Address the concern above.

Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_5: [OUT_OF_SCOPE] Direct Codex exec paths do not use env-key auth helper
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Lint-fix and related direct Codex dispatch paths are outside the current plan and may still use ChatGPT billing or login auth even when `OPENAI_API_KEY` is set.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_6: [OUT_OF_SCOPE] Codex trust-config argv logic is duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `PROJECT_KEY` / `TRUST_CONFIG_ARG` logic is duplicated across Codex launch sites, making future trust-escape changes harder.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

