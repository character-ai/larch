### OOS_1: correctness: python/execution_issues.py:124-127
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Sentinel-match already-flushed branch still truncates execution-issues.md contrary to bash and plan FINDING_4 Step 7a calls flush_execution_issues in-process; when sentinel SHA matches a non-empty log (retry/idempotent replay), Python clears local Tool Failures/Warnings that flush-execution-issues.sh:109-112 preserves On sentinel_matches return already-flushed without issue_log.write_text; truncate only on batch_matches no-records and ok paths; add parity tests
- **Suggested revision**: Address the concern above.


### OOS_2: risk-integration: python/test_execution_issues.py:61-145
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Plan-required sentinel vs batch flush split lacks pytest for batch-only idempotency Step 7a uses Python flush_execution_issues; without a batch-only probe test, a regression in batch_matches could reintroduce duplicate NDJSON or skip log truncation while CI stays green Port the per-section-probe scenario from skills/implement/scripts/test-flush-execution-issues.sh into test_flush_execution_issues_idempotent_when_batch_contains_all_sections
- **Suggested revision**: Address the concern above.


### OOS_3: **correctness** `python/execution_issues.py:124-127` — In `flush_execution_issues()`, the `sentinel_matches` branch writes an empty `execution-issues.md` and returns `already-flushed`. The bash authority (`skills/implement/scripts/flush-execution-issues.sh:109-112`) returns `already-flushed` on sentinel match **without** truncating the issue log; truncation happens only on the separate `batch_matches` branch (`flush-execution-issues.sh:116-124`). After a sentinel-only hit, the Python verb drops in-memory execution issues that bash would keep until a batch match or a successful append. **Suggested fix:** On `sentinel_matches` only, return `already-flushed` without clearing `issue_log`; keep truncation solely on `batch_matches` and post-success paths, matching the shell split called out in the plan.
- **Reviewer**: dyn-wrapper-parity-output.txt
- **Concern**: - **correctness** `python/execution_issues.py:124-127` — In `flush_execution_issues()`, the `sentinel_matches` branch writes an empty `execution-issues.md` and returns `already-flushed`. The bash authority (`skills/implement/scripts/flush-execution-issues.sh:109-112`) returns `already-flushed` on sentinel match **without** truncating the issue log; truncation happens only on the separate `batch_matches` branch (`flush-execution-issues.sh:116-124`). After a sentinel-only hit, the Python verb drops in-memory execution issues that bash would keep until a batch match or a successful append. **Suggested fix:** On `sentinel_matches` only, return `already-flushed` without clearing `issue_log`; keep truncation solely on `batch_matches` and post-success paths, matching the shell split called out in the plan.
- **Suggested revision**: Address the concern above.


### OOS_4: **risk-integration** `python/execution_issues.py:158-188` — `flush_execution_issues_safety_net()` does not mirror the bash contract in `scripts/implement-finalize.sh:220-236`: it never reads or writes `.execution-issues-flushed.sha`, never short-circuits on sentinel/file-sha matches, and never returns `already-flushed`. Without sentinel bookkeeping, idempotent Step 18 replays depend only on per-section batch grep in `write_execution_issues_records`, and a later teardown flush using a different hash scheme can still re-append. **Suggested fix:** Port the bash early-return branches (sentinel match, full-file `source_sha256` in batch, write sentinel on `no-records`/`ok`) into `flush_execution_issues_safety_net()` while keeping the no-truncate invariant; add tests for replay idempotency and sentinel creation.
- **Reviewer**: dyn-safety-net-ledger-output.txt
- **Concern**: - **risk-integration** `python/execution_issues.py:158-188` — `flush_execution_issues_safety_net()` does not mirror the bash contract in `scripts/implement-finalize.sh:220-236`: it never reads or writes `.execution-issues-flushed.sha`, never short-circuits on sentinel/file-sha matches, and never returns `already-flushed`. Without sentinel bookkeeping, idempotent Step 18 replays depend only on per-section batch grep in `write_execution_issues_records`, and a later teardown flush using a different hash scheme can still re-append. **Suggested fix:** Port the bash early-return branches (sentinel match, full-file `source_sha256` in batch, write sentinel on `no-records`/`ok`) into `flush_execution_issues_safety_net()` while keeping the no-truncate invariant; add tests for replay idempotency and sentinel creation.
- **Suggested revision**: Address the concern above.


### OOS_5: **risk-integration** `python/execution_issues.py:124-126` — The Step 7a `sentinel_matches` branch still truncates `execution-issues.md`, but bash `skills/implement/scripts/flush-execution-issues.sh:109-112` returns `already-flushed` without clearing the file. The branch split was an explicit plan acceptance item ("sentinel-match no-truncate; batch-match may truncate"). Truncating on sentinel match can erase stall-time diagnostics that accumulated after the sentinel was written and before Step 18's append-only safety net runs, weakening the ledger boundary between Step 7a checkpoint flush and Step 18 recovery. **Suggested fix:** On `sentinel_matches`, return `already-flushed` without `issue_log.write_text("")`; keep truncation only on `batch_matches`, `no-records`, and successful `ok`; split `python/test_execution_issues.py:61-73` into sentinel-match (preserved log) and batch-match (cleared log) cases.
- **Reviewer**: dyn-safety-net-ledger-output.txt
- **Concern**: - **risk-integration** `python/execution_issues.py:124-126` — The Step 7a `sentinel_matches` branch still truncates `execution-issues.md`, but bash `skills/implement/scripts/flush-execution-issues.sh:109-112` returns `already-flushed` without clearing the file. The branch split was an explicit plan acceptance item ("sentinel-match no-truncate; batch-match may truncate"). Truncating on sentinel match can erase stall-time diagnostics that accumulated after the sentinel was written and before Step 18's append-only safety net runs, weakening the ledger boundary between Step 7a checkpoint flush and Step 18 recovery. **Suggested fix:** On `sentinel_matches`, return `already-flushed` without `issue_log.write_text("")`; keep truncation only on `batch_matches`, `no-records`, and successful `ok`; split `python/test_execution_issues.py:61-73` into sentinel-match (preserved log) and batch-match (cleared log) cases.
- **Suggested revision**: Address the concern above.


### OOS_6: correctness: python/test_execution_issues.py:61-73
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Test asserts empty log on sentinel-match already-flushed encoding wrong contract Merged CI stays green while sentinel no-truncate regression ships; misses plan-required batch vs sentinel coverage Assert non-empty log preserved on sentinel-match; add batch-match truncates test
- **Suggested revision**: Address the concern above.


### OOS_7: correctness: python/execution_issues.py:124-127
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] sentinel-match already-flushed path truncates execution-issues.md Step 7a calls flush_execution_issues; when .execution-issues-flushed.sha matches current file SHA, Python clears the log but bash and accepted FINDING_4 require preserving local diagnostics on sentinel-only idempotent retry On sentinel_matches return already-flushed without issue_log.write_text(""); truncate only on batch_matches ok and no-records paths
- **Suggested revision**: Address the concern above.


### OOS_8: risk-integration: python/test_execution_issues.py:61-73
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] test asserts log cleared on sentinel-match second flush encodes wrong contract Fixing sentinel behavior will fail CI until test is updated; test does not cover required sentinel-preserve vs batch-truncate split Rewrite into sentinel-preserve and batch-truncate cases per bash flush-execution-issues.sh
- **Suggested revision**: Address the concern above.


