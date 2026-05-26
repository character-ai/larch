## Decision 1: Item (1) scope
- **Question**: Is item (1) of issue #2848 (duplication between design_publish_breadcrumbs and larch_log_publish_breadcrumbs) still in scope?
- **Resolution**: Audit + close any residual duplication. The literal duplication described in the issue body was eliminated by #2790/#2849 (which introduced larch_log_publish_breadcrumbs_shared). Still, do a quiet side-by-side sweep of design-log-publish.sh vs larch-log.sh + lib-larch-log.sh and consolidate any remaining copy-paste (manifest writers, file enumerators, error reporters, etc.) in the same PR.
- **Source**: user

## Decision 2: Item (2) pairing mechanism
- **Question**: How should breadcrumb-monitor.sh learn the PID of the paired background process so it can signal it on timeout?
- **Resolution**: Sidecar PID file via env-var convention. Add `--paired-pid-file <PATH>` flag to the monitor. Callers allocate `$LARCH_PAIRED_PID_FILE` (mktemp under `$DESIGN_TMPDIR/breadcrumbs/` etc.), export it before the background launch, and pass `--paired-pid-file` to the monitor. Long-running scripts write `$$` to that file at startup if `LARCH_PAIRED_PID_FILE` is set. Backward-compatible (opt-in).
- **Source**: user

## Decision 3: Signal strategy on timeout
- **Question**: When monitor times out and signals the paired process, what signal strategy should it use?
- **Resolution**: SIGTERM first to let scripts run their own EXIT trap, then SIGKILL after 5 seconds of grace if still alive.
- **Source**: user

## Decision 4: Adoption scope
- **Question**: Which callsites should be updated to use the new --paired-pid-file mechanism in this PR?
- **Resolution**: All current paired callsites (one PR). Update collect-agent-results.sh, ship-pr.sh, run-step5-review.sh, ci-wait.sh, and all other Family B denylisted scripts to write to $LARCH_PAIRED_PID_FILE on startup; update all SKILL.md fenced blocks (design, implement, review) to allocate the path and pass it to monitor.
- **Source**: user

## Decision 5: Lint enforcement
- **Question**: Should scripts/lint-foreground-markers.sh enforce the new contract in this PR?
- **Resolution**: Yes — add lint enforcement. Update lint-foreground-markers.sh + its test harness to require LARCH_PAIRED_PID_FILE allocation in fenced blocks invoking Family B background scripts, and require the monitor invocation in the same block to carry --paired-pid-file pointing at that env var. Hard contract going forward.
- **Source**: user

## Decision 6: Missing pid-file fallback
- **Question**: When LARCH_PAIRED_PID_FILE is set on the background script but the file is missing or has malformed content on monitor timeout, how should the monitor behave?
- **Resolution**: Log a "WARN paired-pid-file-missing" breadcrumb and proceed with current timeout exit code 4. No hard error. Most defensive — preserves existing behavior when pairing data is corrupt while still surfacing a diagnostic.
- **Source**: user

## Decision 7: Audit phase shape
- **Question**: Should the duplication audit be a discrete pre-implementation step or a quiet sweep folded into the PR diff?
- **Resolution**: Quiet sweep folded into the PR diff. No separate audit report; any genuine remaining duplication is added as a Files-to-modify subsection with the consolidation change.
- **Source**: user
