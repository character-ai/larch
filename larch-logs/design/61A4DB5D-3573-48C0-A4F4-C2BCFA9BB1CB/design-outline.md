## Proposed Design Outline

### Goals
- Port all four read modes from `tracking-issue-read.sh` plus `create-issue` and `mark-false-positive` from `tracking-issue-write.sh` into `python/tracking_issue.py`.
- Register CLI verbs `tracking-issue read|create-issue|append-comment|rename|mark-false-positive|upsert-summary` in `python/cli.py`.
- Cut over all shell consumers to `python3 python/cli.py tracking-issue <verb>`, delete the three shell scripts and harnesses, and update manifests and docs.

### Non-goals
- Porting bash library helpers that surviving bash scripts still source (e.g. `lib-quiet.sh`, `lib-net.sh`).
- Adding new tracking-issue behaviors beyond parity with the current shell surface.
- Changing the existing `rename`, `append_comment`, `upsert_summary`, or `upsert_token_report` Python functions (only CLI wiring added).

### Approach sketch
- Add `read` (4 modes: issue+prompt, issue-only, prompt/stdin, sentinel), `create_issue`, and `mark_false_positive` to `python/tracking_issue.py`; reuse `issue_wire.issue_insert_signal_marker_main` for `mark-false-positive`.
- Add CLI `main_*` functions in `python/tracking_issue.py` and register 6 verbs in `python/cli.py` `_REGISTRY`.
- Cut over consumers: `design-publish.sh`, `design-init-runparams.sh`, `render-final-summary.sh`, `implement-bootstrap.sh`, `step-0-bootstrap.sh`, `implement-finalize.sh`, `ship-pr.sh`, and the implement post/refresh/final-report scripts.
- Expand `python/test_tracking_issue.py` for the new functions and CLI verbs.
- Delete `scripts/tracking-issue-{read,write,summary}.{sh,md}` and their harnesses; update `python/migrated-scripts.tsv`, `.gitleaks.toml`, `agent-lint.toml`, `SECURITY.md`, and `AGENTS.md`.

### Surfaces in scope
- `python/tracking_issue.py`
- `python/test_tracking_issue.py`
- `python/cli.py` (`_REGISTRY`)
- `scripts/tracking-issue-read.sh` + `.md` + `scripts/test-tracking-issue-read-sentinel.sh` + `.md`
- `scripts/tracking-issue-write.sh` + `.md` + `scripts/test-tracking-issue-write.sh` + `.md`
- `scripts/tracking-issue-summary.sh` + `.md` + `scripts/test-tracking-issue-summary.sh` + `.md`
- Consumer scripts: `design-publish.sh`, `design-init-runparams.sh`, `render-final-summary.sh`, `implement-bootstrap.sh`, `skills/implement/scripts/step-0-bootstrap.sh`, `implement-finalize.sh`, `ship-pr.sh`, post/refresh/final-report scripts
- `python/migrated-scripts.tsv`, `.gitleaks.toml`, `agent-lint.toml`, `SECURITY.md`, `AGENTS.md`

### Open questions
- None.
