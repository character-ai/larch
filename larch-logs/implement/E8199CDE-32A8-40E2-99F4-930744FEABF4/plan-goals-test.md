## Goal
Wire dynamic reviewer scout (cap=4) through review-and-fix.sh and implement SKILL.md

## Implementation Plan

### Goal
Wire `--dynamic-archetypes` (default cap=4) through `review-and-fix.sh` so every `/implement` run uses the scout for non-trivial diffs.

### Files to modify

**1. `skills/review-and-fix/scripts/review-and-fix.sh`**

a. Add `DYNAMIC_ARCHETYPES_CLI=""` after `CURSOR_AVAILABLE` init (line ~45).

b. Add CLI arg parsing inside the `while` loop:
   ```
   --dynamic-archetypes) DYNAMIC_ARCHETYPES_CLI="${2:?...}"; shift 2 ;;
   --no-dynamic-archetypes) DYNAMIC_ARCHETYPES_CLI="0"; shift ;;
   ```

c. In `run_implement_round()`, after CODEX/CURSOR resolution, add:
   ```bash
   if [[ -n "$DYNAMIC_ARCHETYPES_CLI" ]]; then
       DYNAMIC_ARCHETYPES="$DYNAMIC_ARCHETYPES_CLI"
   elif [[ ${LARCH_DYNAMIC_ARCHETYPES_MAX+x} ]]; then
       DYNAMIC_ARCHETYPES="$LARCH_DYNAMIC_ARCHETYPES_MAX"
   else
       env_val="$(session_get LARCH_DYNAMIC_ARCHETYPES_MAX "")"
       if [[ -n "$env_val" ]]; then
           DYNAMIC_ARCHETYPES="$env_val"
       elif [[ -n "$IMPLEMENT_TMPDIR" ]]; then
           DYNAMIC_ARCHETYPES="4"
       else
           DYNAMIC_ARCHETYPES="0"
       fi
   fi
   case "$DYNAMIC_ARCHETYPES" in
       [0-4]) ;;
       *) larch_err "review-and-fix.sh: --dynamic-archetypes/LARCH_DYNAMIC_ARCHETYPES_MAX must be an integer from 0 to 4"; exit 2 ;;
   esac
   ```

d. Add `--dynamic-archetypes "$DYNAMIC_ARCHETYPES"` to `core_args` (just before `[[ -n "$DIFF_FILE" ]]`).

**2. `scripts/write-session-env.sh`**

a. Add `DYNAMIC_ARCHETYPES_MAX=""` variable.
b. Add `--dynamic-archetypes) DYNAMIC_ARCHETYPES_MAX="$2"; shift 2 ;;` parser.
c. Add validation: must be integer 0-4.
d. Write `LARCH_DYNAMIC_ARCHETYPES_MAX=$DYNAMIC_ARCHETYPES_MAX` to content when non-empty.

**3. `skills/implement/SKILL.md`** (the file being executed as this skill)

Add two flags in the Flags section (after `--no-logs-commit`):
- `--no-dynamic-archetypes`: `no_dynamic_archetypes=true`. Sets `dynamic_archetypes_value=0`. Scout off; static 7-slot panel only.
- `--dynamic-archetypes <N>`: `dynamic_archetypes_value=<N>`. Overrides the default cap (4). Must be 0–4.

When either flag is set, pass `--dynamic-archetypes "$dynamic_archetypes_value"` to the `write-session-env.sh` call at Step 0 (in `session_env_args`).

Update Step 5 header comment to mention the default: `(review-and-fix.sh, up to N rounds; dynamic-archetypes cap=4 by default)`.

### Resolution priority for DYNAMIC_ARCHETYPES in review-and-fix.sh
1. `--dynamic-archetypes` CLI arg
2. `LARCH_DYNAMIC_ARCHETYPES_MAX` process env var  
3. `LARCH_DYNAMIC_ARCHETYPES_MAX` in session-env file
4. `4` (default when `--implement-tmpdir` set)
5. `0` (default in standalone mode)

### Testing/Verification
- `/relevant-checks` passes (pre-commit on modified files, agent-lint on repo)
- `grep -n "dynamic.archetypes" skills/review-and-fix/scripts/review-and-fix.sh` shows new lines
- After implementation, a non-trivial diff run would emit `SCOUT_STATUS=ok` and `DYNAMIC_SLOTS>=1` in `review-core-dispatch.env`

## Test plan
(no test plan section in plan-file)
