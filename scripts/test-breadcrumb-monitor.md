# test-breadcrumb-monitor.sh contract

Offline regression harness for `scripts/breadcrumb-monitor.sh`.

Coverage includes sentinel coupling, surfaced-sentinel resume behavior, live
stream growth, truncation/reset recovery, PEM-redacted failure tails,
path-scope rejection, `RESEARCH_TMPDIR` acceptance, symlink rejection, invalid
category dropping, partial-line retention, redactor-failure drop warnings, and
the fake Family B done-trap path. It also covers the paired-PID timeout path:
TERM signaling, TERM-to-KILL escalation, missing/empty/malformed/multi-line/CRLF
PID files, stale PID kill failures, the `LARCH_BM_TEST_MODE=1` +
`LARCH_BM_TEST_TIMEOUT_SECONDS` test hook, the nested-overwrite regression, and
the nested-parent-`unset LARCH_PAIRED_PID_FILE` safeguard.

Full monitor contract lives in the primary sibling:
`scripts/breadcrumb-monitor.md`.
