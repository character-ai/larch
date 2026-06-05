## Proposed Design Outline

### Goals
- Add per-bucket changed-line counts to the `/implement` final report: code (excluding `larch-logs/`) and larch logs, each shown as `+added/−deleted`.
- Source counts from the GitHub PR files API so they reflect the merged PR and stay correct after `--merge` deletes the local branch.
- Do all computation in a shell helper (gh/jq + arithmetic), never in SKILL.md prose.

### Non-goals
- No change to the `/design` final report; the new bullet is gated to `--skill implement` only.
- No net/churn reinterpretation — added/deleted split only.
- No third "generated-artifacts" bucket; split is purely `larch-logs/` prefix vs everything else.
- No post-merge git work (NEVER #16); the helper is read-only API querying.

### Approach sketch
- New helper `scripts/compute-pr-line-counts.sh` (+ sibling `.md` + `test-*.sh`): given REPO + PR number, page `gh api repos/<repo>/pulls/<N>/files`, bucket additions/deletions by `larch-logs/` prefix, emit KVs (code/logs added/deleted).
- `write-final-report.sh` calls the helper, passes results as new flags into `render-run-summary.sh`; N/A when no PR / repo-unavailable / gh fails.
- `render-run-summary.sh` renders one new implement-only bullet, e.g. `- **Lines (PR diff)**: code +X/−Y · larch-logs +A/−B`; mirror in the degraded fallbacks for schema parity.

### Surfaces in scope
- `scripts/compute-pr-line-counts.sh` (new) + `.md` + harness.
- `skills/implement/scripts/write-final-report.sh` (+ `.md`).
- `scripts/render-run-summary.sh` (+ `.md`).
- Existing harnesses: `test-write-final-report.sh`, `test-render-run-summary-callsites.sh`, `test-step-18b-final-report.sh`.

### Open questions
- None.
