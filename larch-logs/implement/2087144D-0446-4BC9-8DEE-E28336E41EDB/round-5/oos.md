### OOS_1: [OUT_OF_SCOPE] test-upgrade-larch-retention.sh harness could be split by concern
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Harness file grew to 693 lines; new cone cases add bulk but follow a consistent per-case HOME pattern. Splitting into `test-upgrade-larch-cone.sh` and `test-upgrade-larch-retention.sh` is a follow-up readability improvement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Consider splitting into test-upgrade-larch-cone.sh and test-upgrade-larch-retention.sh in a follow-up


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_2: [OUT_OF_SCOPE] get_stable_releases uses first API stable tag not semver max
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Pre-existing: `get_stable_releases` picks the first stable tag from the GitHub API rather than semver-max, which can mis-resolve `LATEST_STABLE` if release list order is not newest-first.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Use semver comparison to select latest stable tag


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_3: [OUT_OF_SCOPE] get_installed_larch_version HOME guard alignment when refactoring
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-bash-state-output.txt
- **Severity**: latent
- **Concern**: Pre-existing divergence: `upgrade-larch.sh`'s `get_installed_larch_version` dereferences `$HOME/.claude/plugins/installed_plugins.json` without an empty-`HOME` guard; the new `release-step7-root.sh` path is safer. Worth aligning when touching install metadata reads.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Consolidate into one sourced helper when refactoring root resolution.
  - From dyn-bash-state-output.txt: (no separate fix beyond consolidation note in concern)


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_4: [OUT_OF_SCOPE] Reconcile prose substring fallback intentionally omitted
- **Reviewer(s)**: dyn-bash-state-output.txt
- **Severity**: latent
- **Concern**: The plan called for a fixed reconcile prose fragment fallback when machine lines are absent; implementation and harness intentionally accept only `LARCH_CONE_RECONCILED=true`. Deliberate tightening increases reliance on machine-line emission being correct (see FINDING_14).
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### OOS_5: [OUT_OF_SCOPE] release-step7.env lives in ephemeral prepare temp dir
- **Reviewer(s)**: dyn-release-step7-output.txt
- **Severity**: latent
- **Concern**: Pre-existing pattern now more visible: `release-step7.env` lives under Step 2's `mktemp` prepare dir with no durable recovery copy (unlike release notes). Step 6-only recovery re-runs cannot read cone/restart flags from a prior partial release.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_6: [OUT_OF_SCOPE] Pre-existing SessionStart advisories interpolate local file contents
- **Reviewer(s)**: dyn-hook-failopen-output.txt
- **Severity**: latent
- **Concern**: Pre-existing SessionStart advisories (e.g. `larch-stalled-run.txt`) interpolate local file contents into `MSG` and then into `jq --arg`; larger prompt-injection surface outside this branch's sparse probe.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_7: [OUT_OF_SCOPE] Sparse probe gated on jq and git availability
- **Reviewer(s)**: dyn-hook-failopen-output.txt
- **Severity**: nit
- **Concern**: Environments missing `jq` never get the sparse drift warning (availability limitation, not a fail-open violation).
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### OOS_8: [OUT_OF_SCOPE] probe_sparse_cone_drift shell-opt restore pattern fragile on future edits
- **Reviewer(s)**: dyn-sparse-install-output.txt
- **Severity**: nit
- **Concern**: `case $-` save/restore in `probe_sparse_cone_drift` is fine as written but fragile if future `set -e`-sensitive additions exit before restoration lines; cleaner idiom would be subshell isolation or bash 4.4+ `local -`.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### OOS_9: [OUT_OF_SCOPE] Misleading cone-drift message on stale-active-root predates this diff
- **Reviewer(s)**: dyn-harness-realism-output.txt
- **Severity**: latent
- **Concern**: When `CURRENT_INSTALLED_VERSION == LATEST_STABLE` but only `PLUGIN_ROOT` basename is stale, the "sparse checkout is out of date" message is semantically wrong. Pre-existing before this diff; new code path makes it more reachable (see FINDING_14 for in-scope fix).
- **Suggested revisions (informational for voters; coder decides)**:

Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

