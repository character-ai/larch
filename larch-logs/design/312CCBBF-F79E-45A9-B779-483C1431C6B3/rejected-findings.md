### [Plan Review] FINDING_17

### FINDING_17: `render-final-summary.sh` and `tracking-issue-summary.sh` not on `scripts/lint-foreground-markers.sh` Family B denylist
- **Reviewers**: Cursor-Foreground-Compliance, Codex-Foreground-Compliance (MEDIUM, 2 dynamic reviewers)
- **Concern**: New foreground Bash blocks invoking `render-final-summary.sh` or `tracking-issue-summary.sh` would not be lint-enforced by `scripts/lint-foreground-markers.sh`. A copied block could be backgrounded without `make lint-foreground-markers` failing. The plan adds foreground banner prose but does not extend the denylist mechanism.
- **Proposed resolution**: Either (a) add `render-final-summary.sh` and `tracking-issue-summary.sh` basenames to `DENYLIST` in `scripts/lint-foreground-markers.sh`, update `scripts/lint-foreground-markers.md`, and update `scripts/test-lint-foreground-markers.sh` fixtures; or (b) explicitly justify in the plan WHY these entrypoints don't need denylist enforcement (e.g., the helper internally serializes — but it doesn't, it calls subprocess).


