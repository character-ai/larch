# test-harness-shards-coverage.sh

Regression harness for Makefile `test-harnesses-N` shard membership. It builds a
unified direct-Bash-leaf inventory (recipe-bearing `test-*` targets with no
pytest, plus `*-bash-harness` leaves), then verifies each leaf is assigned to
exactly one shard, rejects aggregates / pytest recipes / unknown non-leaves in
shard lists, checks the umbrella target references all shard targets, and
requires the shard containing this guard to list it first so partition failures
surface before longer harness work. Standalone aliases that deliberately stay
outside the shards, including `test-classify-bump`, `test-promote-release`,
`test-release-prepare`, `test-release-set-version`, the mixed
`test-stall-recovery-report` aggregate and its Rust
`test-stall-recovery-report-2` / `test-stall-recovery-report-3` aliases, and the
Rust agent-command aliases `test-compose-collector-failure-log`, `test-wait-for-reviewers`,
`test-classify-diff-mode`, `test-gather-branch-context`,
`test-run-external-agent-args`, `test-check-reviewers`,
`test-degraded-tools-gate`, and the Rust run-log alias
`test-refresh-run-logs`, `test-capture-session-transcript`, and
`test-verify-run-log-completeness`, must be listed in `CARVE_OUTS` and
documented beside their Makefile targets. Keep this sibling doc in sync with
the harness whenever shard parsing or Makefile target contracts change.
