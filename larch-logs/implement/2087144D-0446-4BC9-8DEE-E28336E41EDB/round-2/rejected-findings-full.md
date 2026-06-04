### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: Release Step 7/8 env-state and restart gating lack offline harness coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The Step 7 state-file write/read and Step 8 restart-gating behavior are prompt-only, so typos or parsing mistakes could leave operators without required restart guidance after cone repair.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_13: Sparse-dir library documentation omits ShellCheck / agent-lint contract
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `scripts/lib-sparse-dirs.md` lacks the planned note explaining ShellCheck line-1 and `agent-lint.toml` exclusion rationale, making future edits easier to mis-handle.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Release Step 7 dropped the planned reconcile-prose fallback
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-sparse-rooting-output.txt
- **Severity**: important
- **Concern**: Step 7 parses only machine-readable `LARCH_CONE_RECONCILED=true` / `LARCH_NEW_VERSION_INSTALLED=true` lines, while the plan expected a fallback based on same-version reconcile prose. Older, partial, or buggy output could repair the cone without the machine line, causing Step 8 to skip a required restart; tests and docs also contradict the planned fallback.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-sparse-rooting-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Sparse-cone comparison logic is duplicated and handles empty/error cases inconsistently
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, dyn-sparse-git-output.txt
- **Severity**: latent
- **Concern**: `sessionstart-health.sh` and `upgrade-larch.sh` duplicate sparse-cone comparison logic and diverge on empty or failed `git sparse-checkout list` output. Future normalization changes can drift, and operators may get no SessionStart hint while `/upgrade-larch` repeatedly takes a heavy reinstall path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, dyn-sparse-git-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: Already-latest early exit can ignore stale or incomplete active cache contents
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-sparse-rooting-output.txt
- **Severity**: latent
- **Concern**: The early-exit path trusts metadata/latest-version and sparse-cone equality without proving the active `PLUGIN_ROOT` cache actually contains allowlisted directories or matches the metadata version. A stale or partially populated cache can skip reinstall and continue missing newly allowlisted runtime directories.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-sparse-rooting-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: Same-version drift reconcile E2E coverage is incomplete
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The production-drift test stub does not exercise the intended same-version reconcile path or assert absence of a from-X-to-X upgrade banner. RC2 regressions could pass tests through an unconditional upgrade path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

