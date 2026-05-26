# test-breadcrumb-monitor.sh contract

Offline regression harness for `scripts/breadcrumb-monitor.sh`.

Coverage includes sentinel coupling, surfaced-sentinel resume behavior, live
stream growth, truncation/reset recovery, PEM-redacted failure tails,
path-scope rejection, `RESEARCH_TMPDIR` acceptance, symlink rejection, invalid
category dropping, partial-line retention, redactor-failure drop warnings, and
the fake Family B done-trap path.

Full monitor contract lives in the primary sibling:
`scripts/breadcrumb-monitor.md`.
