## Proposed Design Outline

### Goals
- Port ship-pr.sh Phase 5 (PR, merge, logging) to 8 stdlib-only Python modules with colocated tests.
- Idempotent via gh/git ground truth; exhaustive merge result-variant routing; all skip modes (--merge=false, draft, forked, repo-unavailable).
- File-backed, redacted gh bodies; a reusable flush_logs() called before every push/merge and post-merge.

### Non-goals
- No change to the live /implement path (strangler-fig until Phase 7); no wiring.
- No deletion of the source .sh scripts.
- No byte-compatible output format; new typed format reconciled with consumers at Phase 7.

### Approach sketch
- 8 flat modules: run_logs.py (+ tokens.py), tracking_issue.py, pr_body.py, push.py, pr.py, oos.py, merge.py.
- Reuse existing seams: proc.run, config.py, gh.py, git.py, redact.py, logging_util.py, run_context.py.
- merge.py classifies result variants and signals re-rebase on head-divergence; frozen dataclass results.
- Each gh/git side effect goes through the injectable proc.run seam; no live mutations in tests.
- Focused bash-parity tests on high-risk logic (merge variants, redaction, idempotency, mermaid-sanitize, PR-body compose).

### Surfaces in scope
- python/run_logs.py, tokens.py, tracking_issue.py, pr_body.py, push.py, pr.py, oos.py, merge.py
- python/test_<module>.py (colocated unit + focused parity tests)
- Read/port: larch-log.sh, refresh-run-logs.sh, write-final-report.sh, append-token-record.sh, append-execution-issue.sh, append-tool-failure.sh, compose-pr-summary.sh, sanitize-mermaid-fragment.sh, tracking-issue-write.sh, create-pr.sh, gh-pr-body-update.sh, git-push.sh, oos-disposition-gate.sh, merge-pr.sh

### Open questions
- None. All scope decisions resolved in Round 1.
