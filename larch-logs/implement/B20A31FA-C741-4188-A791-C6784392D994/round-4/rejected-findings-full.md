### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: Duplicate Codex trust config construction across launch sites
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Multiple call sites independently escape `PROJECT_KEY` and construct trusted-project `-c` arguments while auth config args are centralized. Future path-escaping or trust-config fixes could land in some launchers but not probes or Step 5 dispatch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: CI launcher sibling docs do not mention new auth-mode harness expectations
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `scripts/launch-codex-ci.md` does not document the new env-key/login argv and leak-check harness expectations, making future CI launcher changes harder to audit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: Inline awk config stripping is hard to maintain
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: The login-branch config strip logic is a large inline awk program in a shared shell library, making future larch-owned config-strip changes risky and hard to fixture.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_22

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_22: Review and CI sibling docs lack explicit Codex argv spine
- **Reviewer(s)**: dyn-launcher-parity-output.txt
- **Severity**: latent
- **Concern**: `launch-review.md` and `launch-codex-ci.md` describe auth mode but not full Codex argv ordering, unlike `launch-codex-implement.md`. This weakens launcher parity auditing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-launcher-parity-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Step 5 Codex dispatch is overly nested and duplicates failure logging
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `run_coder_dispatch` combines temp-home setup, auth prep, Codex execution, logging, and Cursor fallback in one long nested block. The duplicate env-key failure log branches increase drift risk and make cleanup/trap ordering harder to verify.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Codex probe cleanup has redundant inline and trap paths
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `check-reviewers.sh` removes probe temp homes inline while also retaining those paths in `PROBE_DIRS` for the exit trap. This creates redundant cleanup and stale debug state after retries, even if it does not necessarily leak files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: Env-key path does not strip legacy larch-owned Codex config entries
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: In env-key mode, copied `~/.codex/config.toml` is not stripped of legacy `env_key` / `model_provider` lines. File config and argv `-c` overrides may conflict or produce confusing auth behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

