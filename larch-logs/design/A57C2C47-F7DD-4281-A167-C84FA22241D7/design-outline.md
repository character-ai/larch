## Proposed Design Outline

### Goals
- Create `python/voting.py` owning ballot parsing, vote tallies, parse-rate accounting, scoreboard, and judge-vote parsing.
- Cut over all 12 bash consumers to `python3 python/cli.py voting <verb>` directly (no shims).
- Delete 36 retired bash files; pass `make lint`, `py-lint`, and `py-test`.

### Non-goals
- No behavioral changes to thresholds, ballot grammar, or scoring semantics.
- No porting of `is_scope_reduction_block` (stays in bash via `check-scope-reduction-marker.sh`).
- No new external dependencies; stdlib-only.

### Approach sketch
- Port 12 bash scripts into one `python/voting.py` (21 verbs + `lint focus-area-enum`).
- Register verbs in `python/cli.py` using the existing `_REGISTRY` pattern.
- Write `python/test_voting.py` porting 6 bash harness assertion sets.
- Hard-cut consumers (tally scripts, dispatch scripts, review-and-fix, etc.); no shims.
- Delete retired bash + harnesses; sweep stale prose references via `lint-retired-scripts`.

### Surfaces in scope
- `python/voting.py` (new), `python/test_voting.py` (new)
- `python/cli.py`, `python/README.md`, `python/migrated-scripts.tsv`
- `Makefile`, `agent-lint.toml`, `SECURITY.md`, `docs/linting.md`
- `skills/review/scripts/tally-code-votes.sh`, `skills/design/scripts/tally-plan-review.sh`
- `scripts/dispatch-code-voters.sh`, `scripts/dispatch-plan-voters.sh`
- `skills/review-and-fix/scripts/review-and-fix.sh`, `scripts/implement-bootstrap.sh`
- 6 more consumer scripts + 5 harness scripts
- 36 retired files (deletion)

### Open questions
- None.
