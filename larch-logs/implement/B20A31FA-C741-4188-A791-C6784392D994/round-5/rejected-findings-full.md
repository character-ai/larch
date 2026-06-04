### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: Duplicate TOML strip helper infrastructure
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: The two TOML strip helpers duplicate similar awk/multiline/comment-handling infrastructure, increasing the risk that a future fix lands in one path but not the other.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: Auth-mode probe stamp behavior shift is undocumented/untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: New auth-mode-specific Codex probe stamps ignore old `larch-codex-present` stamps, causing upgraded installs to reprobe until new stamps populate without documented or asserted behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: Env-key positive probe cache can mask revoked or bad keys
- **Reviewer(s)**: dyn-auth-flow-output.txt, dyn-probe-cache-output.txt
- **Severity**: important
- **Concern**: A fresh `codex-env-key` positive stamp can be honored until TTL expiry even after the key is revoked, rotated, expired, or quota-blocked, so Step 0 can report Codex available before launch fails.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-auth-flow-output.txt, dyn-probe-cache-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: TOML rewriters lack post-rewrite validation
- **Reviewer(s)**: dyn-toml-strip-output.txt
- **Severity**: important
- **Concern**: The strip helpers can exit successfully after incomplete or unsafe rewrites, so callers may proceed with partially stripped credentials or inconsistent TOML instead of failing closed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-toml-strip-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: CI launcher cleanup trap has latent nounset leak risk
- **Reviewer(s)**: dyn-bash-lifecycle-output.txt
- **Severity**: latent
- **Concern**: `launch-codex-ci.sh` uses bare `$MODEL_ARGS_TMP` in an EXIT trap under `set -u`, so future early-exit edits could skip cleanup and leak temp Codex homes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-lifecycle-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_22

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_22: Probe cleanup leaves stale deleted paths in `PROBE_DIRS`
- **Reviewer(s)**: dyn-bash-lifecycle-output.txt
- **Severity**: nit
- **Concern**: `check-reviewers.sh` removes probe homes eagerly but leaves their paths in `PROBE_DIRS`, making future reuse of the array fragile.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-lifecycle-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_23: Login-mode cached false can survive env-key success and block later login probe
- **Reviewer(s)**: dyn-probe-cache-output.txt
- **Severity**: important
- **Concern**: If login probing cached `false`, then env-key succeeds, and later `OPENAI_API_KEY` is cleared within TTL, the stale login `false` can suppress a live login probe even if login auth now works.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-probe-cache-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_24

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_24: Launcher harnesses lack whitespace-only env-key cases
- **Reviewer(s)**: dyn-launcher-parity-output.txt
- **Severity**: latent
- **Concern**: Launcher-level tests cover set/unset/empty `OPENAI_API_KEY` but not whitespace-only values, leaving parity gaps around login fallback wiring.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-launcher-parity-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: Trust config argument construction is duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `TRUST_CONFIG_ARG` construction is repeated across Codex call sites, risking future probe/review/implement trust-level drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: Duplicate Step 5 env-key failure logging
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `review-and-fix.sh` duplicates `codex-env-key-failure` logging for setup and dispatch failures, making future updates and log greps more fragile.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

