### OOS_1: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 1. **risk-integration** `scripts/launch-claude-subprocess.sh:308-315` — Timing recording still redirects ledger stderr to `/dev/null` and uses `|| true`, so allow-list drift warnings (e.g. for `claude-phase3-dyn-*` waterfall kinds) remain invisible at the launcher boundary even though rows now append. **Suggested fix:** Out of this PR’s scope per plan, but a follow-up could tee warnings to a session log without changing success semantics.
- **Suggested revision**: Address the concern above.


### OOS_2: [OUT_OF_SCOPE] architecture
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 2. **architecture** `scripts/timing-report.sh:207-232` — Terse/summary modes still count only `codex` and `cursor` in `vendor-tasks=(codex=…, cursor=…)`; Claude rows are recorded and appear in full JSON `vendor_task_averages`, but not in those summary counters. **Suggested fix:** Extend terse/summary vendor counting to include `claude` if operators rely on those lines for completeness audits.
- **Suggested revision**: Address the concern above.


### OOS_3: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 1. **risk-integration** `scripts/test-launch-claude-subprocess.sh` — The launcher harness asserts token-ledger (`claude_sub`) behavior for voter/scout kinds but never checks that a timing row lands in `timing-ledger.tsv` when `IMPLEMENT_TMPDIR` is set. **Why out of scope:** Plan explicitly scoped tests to ledger/report unit harnesses and left the launcher unchanged; the removed gate was the root cause, and ledger-level tests cover the contract the launcher calls.
- **Suggested revision**: Address the concern above.


### OOS_4: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 2. **risk-integration** `scripts/launch-claude-subprocess.sh:308-315` — Timing recording still uses `>/dev/null 2>&1 || true`, so ledger warnings (path resolution, flock fail-closed, etc.) remain invisible at the launcher boundary. **Why out of scope:** Pre-existing observability gap; this PR fixes silent *rejection* of valid Claude rows, not general launcher error surfacing (explicit plan non-goal).
- **Suggested revision**: Address the concern above.


