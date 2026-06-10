## Proposed Design Outline

### Goals
- Port `clarify-state.sh`, `clarify-comment-post.sh`, `clarify-label.sh` to `python/clarify.py` with stdlib-only, full parity with shell behavior.
- Expose `clarify state|comment-post|label` verbs via `python/cli.py`; cut over all callers directly (no shims).
- Replace shell harnesses with `python/test_clarify.py` pytest; retire all three scripts + sibling `.md` files.

### Non-goals
- Changing the wire format (`larch:clarify-request/response` markers, `id=N` numbering, `STATE=` output).
- Porting unrelated callers from the issue body scope (F1, F3a, F3c, etc.).
- Adding new clarify features beyond the current behavior.

### Approach sketch
- Add public `issue_label_add`, `issue_label_remove`, `label_create`, `issue_labels_list` in `gh.py`, following the existing transient-retry pattern.
- Write `python/clarify.py` with `clarify_state(runner, issue, *, repo)`, `clarify_comment_post(runner, issue, kind, id, content_file, *, repo)`, `clarify_label(runner, issue, action, *, repo, create_if_missing=False)`.
- Register `("clarify", "state"|"comment-post"|"label")` in `cli.py _REGISTRY` with argparse mains.
- Update callers in `skills/design/SKILL.md`, `skills/implement/SKILL.md`, `.claude/skills/agnix-fix/SKILL.md`, `docs/issue-anchored-plan.md` (clarify sections), `AGENTS.md`, `SECURITY.md`, `scripts/get-issue-context.sh`.
- Add to `python/migrated-scripts.tsv`; update Makefile `test-clarify-*` targets; delete retired files.

### Surfaces in scope
- `python/clarify.py` (new)
- `python/test_clarify.py` (new)
- `python/gh.py` (incremental label/comment wrappers)
- `python/cli.py` (registry entries + argparse mains)
- `python/migrated-scripts.tsv` (retire 8 paths)
- `Makefile` (replace test targets)
- `scripts/clarify-state.sh`, `scripts/clarify-state.md` (delete)
- `scripts/clarify-comment-post.sh`, `scripts/clarify-comment-post.md` (delete)
- `scripts/clarify-label.sh`, `scripts/clarify-label.md` (delete)
- `scripts/test-clarify-state.sh`, `scripts/test-clarify-state.md` (delete)
- `scripts/test-clarify-comment.sh`, `scripts/test-clarify-comment.md` (delete)
- `skills/design/SKILL.md`, `skills/implement/SKILL.md`, `.claude/skills/agnix-fix/SKILL.md`
- `docs/issue-anchored-plan.md` (clarify sections only)
- `AGENTS.md`, `SECURITY.md`, `scripts/get-issue-context.sh`

### Open questions
- None.
