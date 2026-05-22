### DECISION_1: Merge mechanism for log-flush PR
- **Chosen**: Direct `gh pr merge --squash --admin --delete-branch` (not merge-pr.sh)
- **Alternative**: Extend merge-pr.sh with a `--logs-only` mode that skips the CI-pass gate
- **Tension**: merge-pr.sh currently requires mergeStateStatus in {CLEAN,UNSTABLE,HAS_HOOKS,BLOCKED} before --admin attempt; the log-flush PR may have mergeStateStatus=CI_NOT_READY since [skip ci] suppresses CI but the PR may not reach CLEAN immediately. Innovation flagged this; Pragmatic chose direct gh.
- **Impact**: Medium
- **Affected files**: scripts/design-log-publish.sh (new), scripts/merge-pr.sh (only if alternative chosen)

### DECISION_2: Helper script location
- **Chosen**: `scripts/design-log-publish.sh`
- **Alternative**: `skills/design/scripts/design-log-publish.sh`
- **Tension**: Codex-Pragmatic said either location; Codex-Innovation said `scripts/`. `scripts/` is more consistent with larch-log-flush.sh, create-pr.sh, merge-pr.sh (all in scripts/).
- **Impact**: Low
- **Affected files**: scripts/design-log-publish.sh (new), skills/design/SKILL.md (caller)
