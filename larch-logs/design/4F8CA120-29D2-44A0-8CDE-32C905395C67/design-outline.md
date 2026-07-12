## Proposed Design Outline

### Goals
- Give the Step 8 architectural assessment a bounded cross-tool fallback waterfall so a transient empty/unparseable response from one tool no longer stalls a clean, CI-green PR.
- Waterfall order for every assessment: Cursor/Composer-2.5 -> Codex/Terra -> Claude/Sonnet-4-6; advance one lane on any unavailable-class failure; emit `unavailable`/operator-bail only after the last lane is exhausted (per-kind).
- Reuse the existing Cursor/Codex availability and launch machinery rather than adding a parallel tool-selection path.

### Non-goals
- No change to invariant-violation or genuine `dropped` semantics; the waterfall applies only to unavailability (no parseable assessment produced).
- No change to the operator-bail contract or `ASSESSMENT_RESULTS` grammar beyond reporting the last lane's failure detail (#7057 diagnostic preserved).
- No same-lane retry multiplication; one attempt per lane keeps Step 8 bounded.

### Approach sketch
- Extend the coordinator `run()` in `architectural_assessment.py` to iterate a fixed ordered lane list instead of retrying one hardcoded `claude` command.
- Each lane pairs a tool + model with the read-only plan-mode invocation and the existing assessment prompt/parse; advance on empty/unparseable/timeout/non-zero, stop on a parseable assessment.
- Reuse Cursor/Codex launch + availability helpers (the reviewer/dispatcher read-only path); a lane whose binary is unavailable is skipped, not fatal.
- Keep `_persist_unavailable` as the terminal path, reached only after the last lane fails, preserving the last lane's sanitized detail.

### Surfaces in scope
- `python/larch/implement/architectural_assessment.py` (coordinator, launcher lanes, unavailable path).
- Existing Cursor/Codex launch + tool-availability helpers under `python/larch/implement/` (reuse, no fork).
- `skills/implement/scripts/step-8-assessment.sh` (only if adapter observation needs adjustment).
- Assessment unit tests under `python/tests/implement/` (new waterfall reproduction coverage per G-Fix-2).

### Open questions
- Whether the Cursor/Codex launchers can pin Composer-2.5 and Terra and support the `--allowedTools Read --permission-mode plan` read-only shape; resolve by inspecting the reuse helpers during drafting.
- Whether any Bash-adapter change is needed, or the Python coordinator change is fully sufficient.
