## Proposed Design Outline

### Goals
- Create `python/review_dispatch.py` with four ported functions: sentinel polling (`wait_reviewers`), diff classification (`classify_diff`), branch context gathering (`gather_branch_context`), and failure-log composition (`compose_collector_failure_log`).
- Register four `agent` CLI verbs in `python/cli.py` and retarget all 6 direct bash callers to `python3 cli.py agent <verb>`.
- Delete the four bash scripts, their `.md` siblings, their bash test harnesses, and update the migration manifest + Makefile.

### Non-goals
- Porting the larger C1a scripts (`collect-agent-results.sh`, `dispatch-with-waterfall.sh`, `dispatch-code-voters.sh`, `launch-review.sh`) — those are pieces 2-6.
- Adding new behavior beyond faithful translation of what the bash scripts do.
- Changing the stdout grammar or argument interface visible to the six retargeted callers.

### Approach sketch
- Port each bash function verbatim into `review_dispatch.py`, using `subprocess` for git calls and `os`/`pathlib` for file I/O.
- Each CLI verb's `_main(argv)` validates args, delegates to the function, and emits KV via the contract stream (`logging_util` / `emit_kv`).
- Write `python/test_review_dispatch.py` covering argv validation, stdout grammar, fd-3 contract, and key behavioral paths.
- Retarget the 6 callers in-place.
- Delete `.sh`, `.md`, test harnesses; add manifest rows; update Makefile.

### Surfaces in scope
- `python/review_dispatch.py` (new)
- `python/test_review_dispatch.py` (new)
- `python/cli.py` (4 new registry entries)
- `python/migrated-scripts.tsv` (8 new rows)
- `Makefile` (retarget 2 targets, add 1 missing target)
- 6 bash callers retargeted in-place
- Deleted: 4 `.sh`, 4 `.md`, 3 bash test harnesses from `scripts/`

### Open questions
- None.
