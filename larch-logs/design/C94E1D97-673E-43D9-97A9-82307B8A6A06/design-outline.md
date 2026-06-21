## Proposed Design Outline

### Goals
- Finish #3685's half-done migration of `slack-issue-announce.sh`: the `slack issue-announce` verb already ships in `python/pr_body.py`.
- Add the missing pytest coverage and a clean injectable test transport.
- Delete the orphaned bash surface and record the retirement.

### Non-goals
- No re-port to a dedicated module; the function stays in `python/pr_body.py`.
- No behavior change to the `slack issue-announce` verb name, its registry entry, or the `closeout.py` Step 16a call site.
- No change to the output grammar (`STATUS` / `REASON` / `ERROR`) or `--best-effort` exit-0 semantics.

### Approach sketch
- Refactor `slack_issue_announce` in `python/pr_body.py`: drop the `__LARCH_FAKE_CURL` subprocess branch, leaving one `urllib.request.urlopen` POST path.
- Add `python/test_pr_body.py` cases that monkeypatch `urllib.request.urlopen` (posted / skips / failures / best-effort).
- Delete the four orphaned files; update the manifest, residual-bash list, and SKILL.md registry; run lint.

### Surfaces in scope
- `python/pr_body.py`, `python/test_pr_body.py`
- `skills/implement/scripts/slack-issue-announce.{sh,md}`, `test-slack-issue-announce.{sh,md}` (delete)
- `python/migrated-scripts.tsv`, `scripts/residual-bash-paths.txt`, `skills/implement/SKILL.md`

### Open questions
- None.
