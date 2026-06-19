### OOS_1: correctness: python/collect_results.py:756-775
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] resolve_collector_stderr_tail_file omits ns-retry stderr-tail candidate that deleted lib-failed-agent-stderr-tail.sh and the plan required. When only reviewer-a-ns-retry.txt.stderr-tail exists (no -retry.txt.stderr-tail), collector skips ns-retry and may emit base .stderr-tail or no tail — wrong/missing failure diagnostics in collect-results output. After retry-tail check, probe f"{base}-ns-retry.txt.stderr-tail" before launch-stderr / .stderr-tail candidates; add pytest for ns-retry-only selection.
- **Suggested revision**: Address the concern above.


### OOS_2: correctness: python/collect_results.py:756-775
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Plan completeness: collector candidate order was not fully ported when Bash resolver was deleted; only render delegation changed. Same ns-retry-only scenario; branch deletes the Bash resolver without adding equivalent Python logic. Port full Bash resolve_collector_stderr_tail_file ordering into collect_results.py per plan.
- **Suggested revision**: Address the concern above.


### OOS_3: correctness: python/collect_results.py:756-775
- **Reviewer**: codex-specialist-correctness-output.txt
- **Concern**: [important] The collector stderr-tail resolver omits the required ns-retry stderr-tail candidate. If reviewer-ns-retry.txt.stderr-tail is the only useful failure tail, collect-results skips it and may emit no useful tail. Check the ns-retry tail immediately after the regular retry tail.
- **Suggested revision**: Address the concern above.


### OOS_4: correctness: python/collect_results.py:756-775
- **Reviewer**: codex-specialist-edge-cases-output.txt
- **Concern**: [important] Collector stderr-tail resolution omits the ns-retry stderr-tail candidate. If only foo-ns-retry.txt.stderr-tail exists, collector falls through to launch stderr or base tail and loses the most relevant non-substantive retry failure. Check <base>-ns-retry.txt.stderr-tail after retry tail and before phase fallback candidates; add coverage for retry absent and ns-retry present.
- **Suggested revision**: Address the concern above.


### OOS_5: risk-integration: python/collect_results.py:756-775
- **Reviewer**: codex-specialist-testing-output.txt
- **Concern**: [important] resolve_collector_stderr_tail_file skips ns-retry stderr tails despite the required candidate order. If only reviewer-ns-retry.txt.stderr-tail exists, collector drops the relevant retry diagnostics and may show stale/no tail. Check the ns-retry tail immediately after retry tail and add a retry-absent/ns-retry-present regression test.
- **Suggested revision**: Address the concern above.


### OOS_6: **risk-integration** `python/collect_results.py:756-775` — `resolve_collector_stderr_tail_file` still omits the `${stem}-ns-retry.txt.stderr-tail` candidate that the retired Bash helper and the G10 plan both require between retry-tail and phase launch-stderr lookup. When only an NS-retry tail exists (no `${base}-retry.txt.stderr-tail`), the collector falls through to `.launch-stderr` or the base `.stderr-tail`, so `/review` collector §3.8 can emit the wrong failure excerpt or nothing at all for NS-retry-only reviewer failures. **Suggested fix:** After the retry-tail check and before the phase-candidate loop, add the same NS-retry probe the deleted `scripts/lib-failed-agent-stderr-tail.sh` used (`${reviewer_file%.txt}-ns-retry.txt.stderr-tail`), and add a pytest case where only the NS-retry tail exists (no retry tail) to lock the ordering.
- **Reviewer**: dyn-diagnostics-parity-output.txt
- **Concern**: - **risk-integration** `python/collect_results.py:756-775` — `resolve_collector_stderr_tail_file` still omits the `${stem}-ns-retry.txt.stderr-tail` candidate that the retired Bash helper and the G10 plan both require between retry-tail and phase launch-stderr lookup. When only an NS-retry tail exists (no `${base}-retry.txt.stderr-tail`), the collector falls through to `.launch-stderr` or the base `.stderr-tail`, so `/review` collector §3.8 can emit the wrong failure excerpt or nothing at all for NS-retry-only reviewer failures. **Suggested fix:** After the retry-tail check and before the phase-candidate loop, add the same NS-retry probe the deleted `scripts/lib-failed-agent-stderr-tail.sh` used (`${reviewer_file%.txt}-ns-retry.txt.stderr-tail`), and add a pytest case where only the NS-retry tail exists (no retry tail) to lock the ordering.
- **Suggested revision**: Address the concern above.


### OOS_7: [OUT_OF_SCOPE] `_append_implement_launch_failure` (`python/agents.py:4868`) and `_review_failure_source` (`python/agents.py:4016-4027`) still use legacy inline source selection and do not delegate to `resolve_failure_diagnostic_source`; only `_ci_failure_source` was unified in this branch. That predates or sits outside the CI-only unification scope, but implement/review vendor batches may still miss composed `.failure-diag` and retry carriers.
- **Reviewer**: dyn-diagnostics-parity-output.txt
- **Concern**: - `_append_implement_launch_failure` (`python/agents.py:4868`) and `_review_failure_source` (`python/agents.py:4016-4027`) still use legacy inline source selection and do not delegate to `resolve_failure_diagnostic_source`; only `_ci_failure_source` was unified in this branch. That predates or sits outside the CI-only unification scope, but implement/review vendor batches may still miss composed `.failure-diag` and retry carriers.
- **Suggested revision**: Address the concern above.


### OOS_8: [OUT_OF_SCOPE] Plan-required tests for append-time redaction boundary, `_ci_failure_source` delegation, stall 50/8000 regression, and `LARCH_FAILED_AGENT_STDERR_TAIL_LINES=0` behavior appear absent from `python/test_agents.py` despite substantial drafter/resolver coverage elsewhere.
- **Reviewer**: dyn-diagnostics-parity-output.txt
- **Concern**: - Plan-required tests for append-time redaction boundary, `_ci_failure_source` delegation, stall 50/8000 regression, and `LARCH_FAILED_AGENT_STDERR_TAIL_LINES=0` behavior appear absent from `python/test_agents.py` despite substantial drafter/resolver coverage elsewhere.
- **Suggested revision**: Address the concern above.


