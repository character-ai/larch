### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: Release Step 7 root resolution is prompt-only instead of a shared executable resolver
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-release-state-output.txt, dyn-sparse-contract-output.txt
- **Severity**: important
- **Concern**: Release Step 7’s `RESOLVED_ROOT` ordering is described in prose or mirrored only in tests, so `/release` can pick a different plugin root than the harness and run upgrade/prune/stamp logic against the wrong cache.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-release-state-output.txt, dyn-sparse-contract-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: Cone reconcile can uninstall before reinstall success is guaranteed
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Same-version cone repair uninstalls before successful reinstall/verification, so a mid-path failure can leave larch uninstalled and the cone still drifted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: SessionStart drift probe silently skips installs missing `lib-sparse-dirs.sh`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Users on pre-fix/corrupted installs lacking `lib-sparse-dirs.sh` get no sparse-drift advisory until a successful upgrade/restart delivers the library.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: Missing explicit operator error when `lib-sparse-dirs.sh` cannot be sourced
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: A missing/corrupted sparse dirs library currently fails with a generic Bash source error rather than an actionable larch error naming the script root.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_20: Already-latest early exit ignores the active cache version
- **Reviewer(s)**: dyn-upgrade-flow-output.txt
- **Severity**: important
- **Concern**: `already_latest_and_cone_ok()` checks installed metadata against latest stable but not the running `CLAUDE_PLUGIN_ROOT` version, so after an upgrade without restart it can early-exit while the active cache remains stale.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-upgrade-flow-output.txt: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: SessionStart sparse-drift probe is unnecessarily gated on `jq`
- **Reviewer(s)**: dyn-upgrade-flow-output.txt
- **Severity**: latent
- **Concern**: Environments with `git` but without `jq` skip sparse-drift warnings even though the probe can run without jq.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-upgrade-flow-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_26

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_26: SessionStart harness does not actually prove independence from later `PLUGIN_ROOT`
- **Reviewer(s)**: dyn-harness-isolation-output.txt
- **Severity**: latent
- **Concern**: The labeled test only proves `HOOK_CWD` independence and never reaches the later `PLUGIN_ROOT` path, so the intended acceptance criterion remains untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-isolation-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Sparse-cone comparison logic is duplicated outside `lib-sparse-dirs.sh`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-sparse-contract-output.txt
- **Severity**: nit
- **Concern**: SessionStart and upgrade-larch each implement sparse-cone comparison rules separately, so future rule changes can make warn-only and reconcile paths disagree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, dyn-sparse-contract-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: SessionStart tests duplicate the sparse allowlist literal
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, dyn-harness-isolation-output.txt, dyn-sparse-contract-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-sessionstart-health.sh` hardcodes the expected sparse dirs instead of deriving from `lib-sparse-dirs.sh`, allowing allowlist edits to desync SessionStart coverage from production.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, dyn-harness-isolation-output.txt, dyn-sparse-contract-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

