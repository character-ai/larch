## Proposed Design Outline

### Goals
- Stop a hostile or buggy external coder from tampering with the pre-coder snapshots that the #3272 carryover guard trusts.
- Relocate the full pre-coder snapshot set to a location the Codex coder cannot write.
- Preserve #3272 carryover classification and the step5-loop telemetry exactly.

### Non-goals
- Do not narrow or remove the coder's `--add-dir "$round_dir"` grant (separate concern; candidate OOS).
- Do not change which paths count as carryover vs. genuinely-new dirt.
- Do not add new external tools, flags, or config.

### Approach sketch
- Resolve a coder-unreachable snapshot dir outside `--add-dir "$round_dir"` — a sibling under `$IMPLEMENT_TMPDIR`, derived from `round_dir`.
- Write `pre-coder-head.txt`, `pre-coder-tracked-paths.txt`, and `pre-coder-path-diffs/` there; read them from there in the carryover predicate.
- Keep the step5-loop `pre-coder-head.txt` telemetry consumer working.
- Update `test-review-and-fix.sh` carryover cases to the new location.

### Surfaces in scope
- `skills/review-and-fix/scripts/review-and-fix.sh` (snapshot write + predicate reads)
- `skills/review-and-fix/scripts/review-implement-step5-loop.sh` (telemetry consumer)
- `skills/review-and-fix/scripts/test-review-and-fix.sh` (carryover tests)
- Sibling `.md` contracts for the above

### Open questions
- Keep a `round_dir` copy of `pre-coder-head.txt` for telemetry, or repoint step5-loop to the trusted copy? Plan will choose; minimum-change leans toward repointing.
