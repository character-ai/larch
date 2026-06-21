### OOS_1: risk-integration: python/test_progress_report.py:227-278
- **Reviewer**: codex-specialist-testing-output.txt
- **Concern**: [important] Design ranking tests can false-pass because expected results correlate with ledger file mtimes. A regression that ranks by timing-ledger.tsv file mtime instead of parsed legacy row timestamps or pointer fallback could still pass these tests. Invert or neutralize ledger file mtimes after fixture writes so only parsed ledger activity or pointer fallback can select the expected run.
- **Suggested revision**: Address the concern above.


