### REJ_C1: Cursor-Correctness (round 1) [code-review/rejected]

**Finding**: Larch-log session artifacts (manifest.json, plan-goals-test.md, plan-review-tally.json) committed under `larch-logs/implement/45E8E9EB.../` are described as unrelated scope noise that should not be in the PR.
**Reason not implemented**: These are normal larch-log flush commits produced by `git-commit.sh` as part of the standard workflow. The run-log artifacts track this implementation session and are intentionally committed to the branch. They are not scope noise — they are a documented part of the larch `run-log` contract and will be merged as part of every implementation PR.

### REJ_C2: Cursor-Correctness (round 1) — Nit [code-review/rejected]

**Finding**: `tally-votes.md` line 7 says "Stdout is `KEY=value` only" which is slightly imprecise under `larch_quiet_init` (contract lines go to FD3, not stdout).
**Reason not implemented**: The wording is consistent with other contract docs in the codebase and the existing .md already accurately describes the contract stream. The accepted finding (emit_kv contract fix) is the higher-value change; touching wording further is unnecessary churn.

