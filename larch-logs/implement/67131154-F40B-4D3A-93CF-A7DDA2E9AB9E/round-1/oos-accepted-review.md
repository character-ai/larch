### OOS_1: [OUT_OF_SCOPE] Misleading skip warning when ledger exists but lacks marks
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: When a ledger is present but rejected (no marks), the scan reuses the missing-canonical-file warning. Operators misdiagnose markless ledgers as missing `token-report-final.json`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Emit a distinct warning when the ledger exists but `build_report_from_ledgers` fails.


### OOS_2: [OUT_OF_SCOPE] Distinct warning for markless ledger vs missing canonical
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Skip message cites missing `token-report-final.json` when ledger exists but lacks marks. Operators misdiagnose markless ledgers as missing canonical report.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Use distinct warnings for missing canonical vs unusable ledger (e.g. no step marks).


