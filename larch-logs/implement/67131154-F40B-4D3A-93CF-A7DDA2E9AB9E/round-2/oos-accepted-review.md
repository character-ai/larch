### OOS_3: [OUT_OF_SCOPE] run-logs.md omits session-id retention and vendor-only recovery limits
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Consumer-safety docs omit `session-id` multi-ledger dependency and Claude omission on fallback. Operators assume full run cost is recovered when only vendor lanes are priced.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### OOS_4: [OUT_OF_SCOPE] Implement GC does not retain larch-tokens-*.jsonl
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Implement GC does not retain `larch-tokens-*.jsonl` though implement ledger fallback exists in `report_tokens_scan`. After gc-run-logs slimming, early-bail implement runs with only a ledger lose recoverable cost data again unless implement symmetry is added.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Extend `_keep_file` or `SKILL_KEEP` for implement ledgers if implement symmetry is desired.


