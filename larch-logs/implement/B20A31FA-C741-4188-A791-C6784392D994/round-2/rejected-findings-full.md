### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: env-key probe mode bypasses true cache hits
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `scripts/check-reviewers.sh` bypasses all env-key probe cache stamps, including fresh `true` hits, causing every session setup with env-key mode to re-run the Codex probe.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_19: copied temp Codex config may duplicate literal secrets
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-auth-secrets-output.txt
- **Severity**: latent
- **Concern**: covered paths copy full `~/.codex/config.toml` into temp `CODEX_HOME`. If an operator has misconfigured literal API keys or other secrets in that config, those secrets are duplicated under `/tmp`; documentation may overclaim that keys are not present in copied config files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, dyn-auth-secrets-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_24

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_24: env-key branch keeps old larch env-key config on disk
- **Reviewer(s)**: dyn-launcher-parity-output.txt
- **Severity**: important
- **Concern**: on the env-key branch, `external_prepare_codex_auth` returns without stripping old larch-owned `model_provider` / `env_key` config from copied `~/.codex/config.toml`. Operators migrating from the old config pattern can still carry conflicting disk config alongside argv-only auth overrides.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-launcher-parity-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_29

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_29: probe cache can report stale login availability after env-key use
- **Reviewer(s)**: dyn-probe-cache-output.txt
- **Severity**: important
- **Concern**: after env-key probes, login-mode stamps are not refreshed or invalidated. If the operator later unsets the key while a stale fresh `codex-login` true stamp remains, `CODEX_PRESENT=true` can be reported without rechecking current login auth.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-probe-cache-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: trusted-project config argv construction is duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `PROJECT_KEY` / `TRUST_CONFIG_ARG` construction is duplicated across five Codex launcher/probe call sites, so future escaping or formatting changes can drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: temp CODEX_HOME bootstrap is duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: temp `CODEX_HOME` setup logic is duplicated between `scripts/check-reviewers.sh` and `skills/review-and-fix/scripts/review-and-fix.sh`, risking lifecycle, copy-order, or error-handling drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: probe cleanup uses overlapping strategies
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/check-reviewers.sh` mixes inline `rm -rf` with `PROBE_DIRS` EXIT cleanup, making auth-retry cleanup paths harder to reason about and leaving deleted paths accumulated in the trap list.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: embedded awk stripper is a complexity hotspot
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: the large embedded awk program in `scripts/lib-external-launcher-common.sh` is dense shared-library logic; future strip rules may make it harder to maintain safely.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

