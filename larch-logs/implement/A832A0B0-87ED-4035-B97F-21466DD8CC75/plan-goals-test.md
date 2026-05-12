## Goal
Eliminate turn boundary at post-bump step in /implement that causes context compaction requiring user input (issue #1944).

## Implementation Plan
## Goal
Eliminate the turn boundary at the post-bump step in `/implement` that causes context compaction + recap requiring user input (issue #1944).

## Root Cause
`ship-pr.sh` handles the version bump internally (calling `classify-bump.sh` and `apply-bump.sh` directly) since v26.0.15, but `SKILL.md` still has:
1. NEVER #11 referring to `/bump-version` as a direct Skill call by the orchestrator
2. Anti-halt reminder saying "after Step 8's pre-bump-decision branches resolve (whether via `/bump-version` returning...)" — old path
3. Instruction "The `✅ 8: version bump` breadcrumb is printed ONLY at the `STATUS=ok/skipped` branch after `postbump` completes" — causes orchestrator to print it as TEXT OUTPUT after ship-pr.sh exits

When the orchestrator prints "✅ 8: version bump" as text output, it creates a turn boundary. If context is full at that point, compaction fires and the recap requires "continue".

## Implementation Plan

### 1. ship-pr.sh — add breadcrumb to `run_bump_phase()`
In `run_bump_phase()`, in the `ok|skipped` case, add breadcrumb printing BEFORE `advance_phase pr-prep`:
```bash
case "$status" in
    ok|skipped)
        local _cur _new _btype
        _cur=$(kv_value CURRENT_VERSION "$classify_out")
        _new=$(read_state NEW_VERSION)
        _btype=$(read_state BUMP_TYPE)
        case "$_btype" in
            PATCH|MINOR|MAJOR)
                printf '✅ 8: version bump — %s → %s (%s)\n' "$_cur" "$_new" "$_btype"
                ;;
            *)
                if [ "$forked" = "true" ]; then
                    printf '⏩ 8: version bump status=skip reason=forked\n'
                else
                    printf '⏩ 8: version bump status=skip reason=%s\n' "${_btype:-NONE}"
                fi
                ;;
        esac
        advance_phase pr-prep
        ;;
```

The variables `classify_out`, `forked`, etc. are already in scope in `run_bump_phase`.

### 2. SKILL.md — update NEVER #11
Replace the current NEVER #11 (which says "NEVER write any text output between `/bump-version`'s return and the `postbump-state.sh` Write") with:

"**NEVER call `/bump-version` as a direct Skill invocation from the Step 8+ orchestrator, and NEVER print `✅ 8: version bump` or `⏩ 8: version bump` as orchestrator text output.** **Why**: `ship-pr.sh` handles the version bump internally (calling `classify-bump.sh` and `apply-bump.sh` as shell commands) and emits the `✅ 8:` / `⏩ 8:` breadcrumb lines to its own stdout. Printing the breadcrumb as orchestrator text output creates a turn boundary at the post-bump point — when the context is full, context compaction fires and the recap requires user input (issue #1944). The `.bump-version-armed` Stop-hook sentinel is not written in the ship-pr.sh path. **How to apply**: in Step 8+, the orchestrator's ONLY action related to version bump is writing `ship-pr-state.sh` and calling `ship-pr.sh`. Do NOT add any `/bump-version` Skill calls or any `✅ 8:` / `⏩ 8:` text output."

### 3. SKILL.md — update anti-halt reminder (line 14)
Replace the "Critical boundary: after Step 8's pre-bump-decision branches resolve..." sentence with:
"**Critical boundary: after `ship-pr.sh` exits (any exit code), do NOT print `✅ 8: version bump`, `⏩ 8: version bump`, or any other Step 8 breadcrumb as orchestrator text output — `ship-pr.sh` emits these lines to its own stdout (issue #1944). Parse `ship-pr-state.sh` silently and re-invoke per the Step 8+ exit-code table.**"

### 4. ship-pr.md — add note about breadcrumb output
Add a note to the "Helper Contracts" or "Invariants" section that `run_bump_phase` emits a human-readable `✅ 8:` or `⏩ 8:` breadcrumb line to stdout after postbump completes.

## Files to Modify
- `scripts/ship-pr.sh` — add breadcrumb printing in `run_bump_phase()`
- `skills/implement/SKILL.md` — update NEVER #11 and anti-halt reminder
- `scripts/ship-pr.md` — document the breadcrumb output

## Edge Cases
- BUMP_TYPE=NONE (no bump needed): print `⏩ 8: version bump status=skip reason=NONE`
- forked=true: print `⏩ 8: version bump status=skip reason=forked`
- has_bump=false: `classify_out` is empty, BUMP_TYPE=NONE (same skip path)
- STATUS=skipped from finalize (forked path): forked variable handles this

## Testing
- Run `make lint` / `make test-ship-pr` to verify no regressions
- Verify breadcrumb appears in ship-pr.sh stdout (grep the test fixtures)
- Verify SKILL.md passes agent-lint (S017 check, description trigger)

## Test plan
- Run make lint / make test-ship-pr
- Verify breadcrumb in ship-pr.sh stdout
- Verify SKILL.md passes agent-lint
