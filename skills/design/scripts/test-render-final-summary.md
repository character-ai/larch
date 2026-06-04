# test-render-final-summary.sh

Offline harness for `skills/design/scripts/render-final-summary.sh`: approved path
(`cmp` byte identity between stdout and `final-summary.md`), cancelled outcome
bullet, invalid outcome exit code 2, per-agent cost breakdown, token-data-missing
`--cost-unavailable`, renderer fallback, and early-cancellation empty-mode
normalization.

## Recent contract coverage

- Covers `publish-skipped` in primary and degraded fallback render paths: Outcome bullet, skipped-publish note, `Run logs` `N/A`, no recovery prose, and stdout/file identity.
