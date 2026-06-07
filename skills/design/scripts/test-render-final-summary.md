# test-render-final-summary.sh

Offline harness for `skills/design/scripts/render-final-summary.sh`: approved path
(`cmp` byte identity between stdout and `final-summary.md`), cancelled outcome
bullet, invalid outcome exit code 2, per-agent cost breakdown, token-data-missing
`--cost-unavailable`, renderer fallback, and early-cancellation empty-mode
normalization.

## Recent contract coverage

- Covers `publish-skipped` in primary and degraded fallback render paths: Outcome bullet, skipped-publish note, `Run logs` `N/A`, no recovery prose, and stdout/file identity.
- Covers Plan review non-zero count: fixture uses `- **Focus area**: <value>` format; asserts the Plan review line shows a count ≥ 1 when `accepted-plan-findings.md` has `### FINDING_N:` blocks. Covers OOS combined count: FINDING_+OOS_ blocks are both counted.
