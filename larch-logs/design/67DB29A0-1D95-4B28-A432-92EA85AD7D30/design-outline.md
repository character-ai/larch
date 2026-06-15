## Proposed Design Outline

### Goals
- Ensure all background processes spawned during Step 3 plan review are killed when `design-step3-review.sh` exits.
- Prevent orphan shells from appearing in Claude Code's active-shell count after `/design` completes.
- Add BASH_AUTHORING.md documentation for the large-variable heredoc anti-pattern.

### Non-goals
- Changing `/implement`'s cleanup behavior (already handled by `finalize.py` at its cleanup phase).
- Modifying reviewer timeout values (`--timeout 1860`).
- Adding new retry or fallback logic for failed reviewer processes.

### Approach sketch
- **Fix 1**: Add `set +m` at the top of `run-step3-review.sh`'s loop body to block inheritance of monitor mode from the wrapper; this keeps `dispatch-with-waterfall.sh`'s `( )&` children in PG_R, making the existing `kill -- -PG_R` effective.
- **Fix 2**: Add EXIT trap to `dispatch-with-waterfall.sh` that kills the tracked `pids` array on exit.
- **Fix 4**: Expose `kill_session_background_processes` (already in `finalize.py`) as `python3 python/cli.py session kill-background-processes --design-tmpdir PATH`; call it from `design-step3-review.sh` after the `kill -- -PG_R` call as belt-and-suspenders.
- **Fix 3**: Add a note to BASH_AUTHORING.md about the `cat > file << EOF\n${LARGE_VAR}\nEOF` anti-pattern in `run_in_background` Bash calls.

### Surfaces in scope
- `skills/design/scripts/design-step3-review.sh`
- `skills/design/scripts/run-step3-review.sh`
- `scripts/dispatch-with-waterfall.sh`, `scripts/dispatch-with-waterfall.md`
- `python/cli.py`, `python/session_env.py`, `python/finalize.py`
- `BASH_AUTHORING.md`
- Sibling `.md` contracts for any changed scripts

### Open questions
- None.
