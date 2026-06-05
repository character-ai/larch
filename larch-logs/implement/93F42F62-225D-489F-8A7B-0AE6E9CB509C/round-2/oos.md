### FINDING_20: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **security** `scripts/design-pause-load.sh:308-311` — `cp -R "$restore_tmp"/. "$DESIGN_TMPDIR"/` merges into the destination without clearing pre-existing tmpdir files first. A partial failed `cp` (or stale files already in `$DESIGN_TMPDIR`) can leave artifacts that are not part of the restored snapshot on retry. **Suggested fix:** This predates the branch; if hardening is desired, stage into a clean tmpdir or delete destination contents before install (same pattern as publish-side containment).
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_21: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **security** `SECURITY.md` (pause/resume paragraph, pre-change) — Main previously documented “rejects extracted symlinks,” but `design-pause-load.sh` on `main` never implemented an explicit post-extract symlink scan; it used `git archive | tar -x`. The new `git show` path is effectively safer for symlink objects. **Suggested fix:** Optional defense-in-depth: `find "$restore_tmp" -type l` (and reject) immediately before `cp -R`, matching `design-log-publish.sh` posture — not a regression, but would align docs and code.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_22: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 3. **risk-integration** `python/ship.py` (commit `21d62ab59`, #3448) — Large resume/ship refactor is unrelated to pause/resume; round-1 follow-up (`_MIN_GH_SKIPPED_MERGE_SIGNALS`, `post-merge-sentinel` gating for `manifest_done`) appears to *strengthen* merge-resume trust, not weaken it. Full audit of that surface belongs to the #3448 / Phase 7 ship review called out in `SECURITY.md`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_31: [OUT_OF_SCOPE] The new `ls-tree` capture (`if ! git … ls-tree … >"$enum_tmp"`) and per-path `if ! git show` guards in `scripts/design-pause-load.sh:232-250` correctly follow the `scripts/scrub-log-secrets.sh:176-185` pattern and avoid the `set -euo pipefail` pitfall where a failed `ls-tree` inside process substitution would masquerade as `missing-restored-artifact`.
- **Reviewer**: dyn-shell-failure-output.txt
- **Concern**: - The new `ls-tree` capture (`if ! git … ls-tree … >"$enum_tmp"`) and per-path `if ! git show` guards in `scripts/design-pause-load.sh:232-250` correctly follow the `scripts/scrub-log-secrets.sh:176-185` pattern and avoid the `set -euo pipefail` pitfall where a failed `ls-tree` inside process substitution would masquerade as `missing-restored-artifact`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_32: [OUT_OF_SCOPE] `design-route.sh` appends every `WARN=` line into `WARN_LINES[]` (`skills/design/scripts/design-route.sh:310`), so combined `WARN=body-drift` + `WARN=marker-delete-failed` output is not dropped by the primary resume consumer.
- **Reviewer**: dyn-shell-failure-output.txt
- **Concern**: - `design-route.sh` appends every `WARN=` line into `WARN_LINES[]` (`skills/design/scripts/design-route.sh:310`), so combined `WARN=body-drift` + `WARN=marker-delete-failed` output is not dropped by the primary resume consumer.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_33: [OUT_OF_SCOPE] `scripts/design-log-publish.sh:589-598` driver-phase allowlist (WI1) is narrow and consistent with `skills/design/scripts/design-driver.sh` flat `.completed/$step_name` writes; negative coverage for `.completed/bogus` exists in `scripts/test-design-log-publish.sh`.
- **Reviewer**: dyn-shell-failure-output.txt
- **Concern**: - `scripts/design-log-publish.sh:589-598` driver-phase allowlist (WI1) is narrow and consistent with `skills/design/scripts/design-driver.sh` flat `.completed/$step_name` writes; negative coverage for `.completed/bogus` exists in `scripts/test-design-log-publish.sh`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_34: [OUT_OF_SCOPE] Pre-existing: `scripts/design-log-publish.sh:615` still stages `.completed` via `done < <(find …)` without an explicit `find` failure guard; not introduced by this branch.
- **Reviewer**: dyn-shell-failure-output.txt
- **Concern**: - Pre-existing: `scripts/design-log-publish.sh:615` still stages `.completed` via `done < <(find …)` without an explicit `find` failure guard; not introduced by this branch.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_39: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: dyn-git-snapshot-output.txt
- **Concern**: - **risk-integration** `scripts/design-pause-load.sh:322-326` — When both body drift and marker-delete fail, two `WARN=` lines are emitted; `design-route.sh` accumulates all `WARN` values, but any downstream consumer that keeps only the last `WARN` will drop `body-drift`. Consider comma-joining or a second keyed warning if that surfaces in practice.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_40: [OUT_OF_SCOPE] The branch also carries unrelated `python/` ship/CI-monitor changes from commit `21d62ab59` (#3448); they are outside the pause/resume snapshot-restore surface reviewed here.
- **Reviewer**: dyn-git-snapshot-output.txt
- **Concern**: - The branch also carries unrelated `python/` ship/CI-monitor changes from commit `21d62ab59` (#3448); they are outside the pause/resume snapshot-restore surface reviewed here.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_41: [OUT_OF_SCOPE] WI1 (`design-log-publish.sh` driver phase-sentinel allowlist) and WI2 (`ls-tree`+`show` bypassing `export-ignore`) match the stated plan; path-prefix guards at `scripts/design-pause-load.sh:239-245` and the real-git export-ignore fixture are appropriate mitigations for the restore primitive change.
- **Reviewer**: dyn-git-snapshot-output.txt
- **Concern**: - WI1 (`design-log-publish.sh` driver phase-sentinel allowlist) and WI2 (`ls-tree`+`show` bypassing `export-ignore`) match the stated plan; path-prefix guards at `scripts/design-pause-load.sh:239-245` and the real-git export-ignore fixture are appropriate mitigations for the restore primitive change.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_42: **architecture** `skills/design/scripts/design-route.sh:292-375` — WI3 keeps the pause marker on loader failures so operators can retry, but `design-route.sh` still treats `LOAD_OK=false` as fallthrough into title/re-entry/plan routing (`design-route.md` line 31) instead of emitting `ROUTE=cancel-pause-load`. On the normal paused issue (`[DESIGNING]` from `design-init-runparams.sh`), a retryable failure such as `ERROR=snapshot-not-found` or `ERROR=missing-restored-artifact` therefore ends in `ROUTE=cancel-title-filter` with the lifecycle rename banner, while the structured loader `ERROR=` is secondary. That recreates the #3506 failure mode the branch set out to fix: the marker survives, but `/design` aborts with misleading “rename the title” guidance until the snapshot is fixed. **Suggested fix:** When `pause_marker_present` and `LOAD_OK=false` (or loader exit ≠ 0), set `ROUTE=cancel-pause-load`, forward the loader `ERROR=` into `ERROR_LINES`, and exit before title-eligibility; reserve fallthrough only for `no-pause-marker` paths.
- **Reviewer**: dyn-resume-state-output.txt
- **Concern**: - **architecture** `skills/design/scripts/design-route.sh:292-375` — WI3 keeps the pause marker on loader failures so operators can retry, but `design-route.sh` still treats `LOAD_OK=false` as fallthrough into title/re-entry/plan routing (`design-route.md` line 31) instead of emitting `ROUTE=cancel-pause-load`. On the normal paused issue (`[DESIGNING]` from `design-init-runparams.sh`), a retryable failure such as `ERROR=snapshot-not-found` or `ERROR=missing-restored-artifact` therefore ends in `ROUTE=cancel-title-filter` with the lifecycle rename banner, while the structured loader `ERROR=` is secondary. That recreates the #3506 failure mode the branch set out to fix: the marker survives, but `/design` aborts with misleading “rename the title” guidance until the snapshot is fixed. **Suggested fix:** When `pause_marker_present` and `LOAD_OK=false` (or loader exit ≠ 0), set `ROUTE=cancel-pause-load`, forward the loader `ERROR=` into `ERROR_LINES`, and exit before title-eligibility; reserve fallthrough only for `no-pause-marker` paths.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_45: [OUT_OF_SCOPE] The precomputed diff at `round-2/diff.txt` also includes large `python/ship.py` / `python/test_ship.py` changes and an implement run-log commit (`8b4235514`) that are unrelated to pause/resume; review those separately if the PR scope is meant to be pause-only.
- **Reviewer**: dyn-resume-state-output.txt
- **Concern**: - The precomputed diff at `round-2/diff.txt` also includes large `python/ship.py` / `python/test_ship.py` changes and an implement run-log commit (`8b4235514`) that are unrelated to pause/resume; review those separately if the PR scope is meant to be pause-only.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_46: [OUT_OF_SCOPE] `design-pause-load.sh:203-204` binds `REPO_TOP` from the caller’s cwd (`git rev-parse --show-toplevel`) while `gh` uses `--repo`; the new real-git export-ignore test documents this cwd requirement. Cross-worktree resume without `cd` into the consumer clone remains a pre-existing footgun, not introduced here.
- **Reviewer**: dyn-resume-state-output.txt
- **Concern**: - `design-pause-load.sh:203-204` binds `REPO_TOP` from the caller’s cwd (`git rev-parse --show-toplevel`) while `gh` uses `--repo`; the new real-git export-ignore test documents this cwd requirement. Cross-worktree resume without `cd` into the consumer clone remains a pre-existing footgun, not introduced here.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_47: [OUT_OF_SCOPE] WI1’s four-name allowlist in `scripts/design-log-publish.sh:589-598` matches `skills/design/scripts/design-driver.sh:61-63,112` today; future driver actions still require dual-side updates (plan failure mode 1).
- **Reviewer**: dyn-resume-state-output.txt
- **Concern**: - WI1’s four-name allowlist in `scripts/design-log-publish.sh:589-598` matches `skills/design/scripts/design-driver.sh:61-63,112` today; future driver actions still require dual-side updates (plan failure mode 1).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

