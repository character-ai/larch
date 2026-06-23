# Review Round 2

- Mode: `diff`
- 1 accepted, 2 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Design GC retains ledgers but drops session-id, breaking multi-ledger recovery
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-generic-output.txt
- **Severity**: important
- **Concern**: GC keeps `larch-tokens-*.jsonl` but not `session-id`, while `report_tokens_scan` uses `session-id` to disambiguate multiple ledgers. After gc-run-logs slimming, a design run with two `larch-tokens-*.jsonl` files and no `token-report-final.json` loses `session-id`; `_session_scoped_ledger_path` returns None and the run is skipped again despite retained ledgers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From codex-generic-output.txt: Add `session-id` to the design consumer-core keep set, or change the scanner/GC contract so multi-ledger slimmed runs remain resolvable. Add a regression test that slims a design run with `session-id` and two ledgers, then verifies scan still recovers the scoped ledger.


