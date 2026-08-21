
## Escalation ledger-ready JSON keys

Rust `ship pr` keeps stdout as exactly one JSON object. For Step 8+ `NEEDS_USER_INPUT` handoffs that route to Main Claude, the object carries ledger-ready data under these pinned keys: `ledger_ready`, `ledger_site`, `ledger_trigger`, `ledger_step`, `ledger_phase`, `ledger_dispatcher`, `ledger_exit_code`, and `ledger_failure_detail_log`. The orchestrator records once before Main Claude edits. The driver does not append duplicate ledger rows.
