# Review Round 1

- Mode: `diff`
- 3 accepted, 3 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Ledger fallback skipped when canonical token report exists but is unusable
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-dyn-cost-recovery-output.txt
- **Severity**: important
- **Concern**: `_resolve_report` only calls `_ledger_fallback_report` when `token-report-final.json` (or legacy `token-report.json`) is absent. If the canonical file exists but is empty, corrupt, unparsable, or lacks usable/numeric vendor totals, the scan returns without attempting ledger recovery even when `larch-tokens-*.jsonl` contains priceable vendor data. Runs are skipped or undercounted (e.g. design dirs with stub canonical JSON plus nonzero ledger marks).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: After canonical load/validation fails, attempt `_ledger_fallback_report` before returning None.
  - From codex-specialist-correctness-output.txt: Try ledger and token-report.ndjson fallback whenever canonical parsing or numeric-token validation fails.
  - From cursor-specialist-edge-cases-output.txt: After canonical load/validation failure, try `_ledger_fallback_report` before final skip; warn when recovering from ledger.
  - From codex-specialist-edge-cases-output.txt: For design runs with ledgers, merge missing or zero vendor lanes from `tokens.build_report_from_ledgers(...)` into the canonical report while preserving the canonical Claude lane.
  - From codex-specialist-testing-output.txt: Fall back to the ledger when the canonical report is unparsable, empty, or lacks usable vendor totals, and cover that case with a regression test.
  - From dyn-dyn-cost-recovery-output.txt: After a failed canonical load or failed `_has_numeric_tokens` on the canonical path, attempt `_ledger_fallback_report` before emitting the skip warning; prefer ledger totals when the canonical file is empty or lacks numeric tokens.


### FINDING_7: `_ledger_fallback_report` does not catch `OSError`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `_ledger_fallback_report` catches `ValueError` only; `OSError` from ledger open/read propagates and can abort the entire scan. One run dir with an unreadable `larch-tokens-*.jsonl` causes `report-tokens analyze` to fail instead of skipping that run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Wrap ledger read/build in try/except `OSError`; warn with `run_dir` path; return None.


### FINDING_9: Ledger fallback merges all globbed ledgers instead of session-scoped ledger
- **Reviewer(s)**: dyn-dyn-cost-recovery-output.txt
- **Severity**: important
- **Concern**: `_ledger_fallback_report` globs and merges every `larch-tokens-*.jsonl` in the run directory, but the canonical token report path uses exactly one ledger via `resolve_token_ledger_path` (`larch-tokens-{sha256(session-id)}.jsonl` from `run_dir/session-id`). Committed design dirs already have multiple ledgers; merging orphan or foreign-session ledgers can change step boundaries and inflate vendor totals versus what `token-report-final.json` would have produced.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-cost-recovery-output.txt: In `_ledger_fallback_report`, resolve the canonical ledger from `run_dir/session-id` (same rule as `resolve_token_ledger_path`, but rooted at `run_dir`), call `build_report_from_ledgers` with that single path, and only if `session-id` is missing fall back to a single-ledger heuristic (e.g. exactly one non-symlink `larch-tokens-*.jsonl`), never blind merge of all glob matches.


