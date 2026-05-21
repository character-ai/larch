## Goal
Add silent retry loop (cap 10) to apply-bump.sh for parallel-clone collision recovery

## Implementation Plan

### Goal
Add a silent retry loop (cap 10) to `apply-bump.sh` so that parallel-clone bump races are recovered automatically instead of requiring manual operator intervention. Each retry re-classifies the bump relative to the new `origin/main` version and emits a breadcrumb on the quiet stream.

### Files to modify

1. `.claude/skills/bump-version/scripts/apply-bump.sh` — add retry loop
2. `.claude/skills/bump-version/scripts/apply-bump.md` — update contract, invariants, test-harness coverage
3. `scripts/test-apply-bump.sh` — add 5 new collision/retry fixtures (K–O)
4. `scripts/test-apply-bump.md` — update coverage summary

### Approach for apply-bump.sh

**New helpers (added before the arg-parsing block):**

```bash
_infer_bump_type() {
  # Infers MAJOR/MINOR/PATCH from (original_current_version, initial_new_version).
  local cur_maj cur_min cur_pat new_maj new_min
  IFS='.' read -r cur_maj cur_min cur_pat <<< "$1"
  IFS='.' read -r new_maj new_min _ <<< "$2"
  if [[ $new_maj -gt $cur_maj ]]; then echo "MAJOR"
  elif [[ $new_min -gt $cur_min ]]; then echo "MINOR"
  else echo "PATCH"
  fi
}

_apply_bump_type() {
  # Computes version by applying BUMP_TYPE to a base version.
  local maj min pat
  IFS='.' read -r maj min pat <<< "$1"
  case "$2" in
    MAJOR) echo "$((maj+1)).0.0" ;;
    MINOR) echo "$maj.$((min+1)).0" ;;
    *)     echo "$maj.$min.$((pat+1))" ;;
  esac
}
```

**Extract ORIGINAL_CURRENT_VERSION** after the plugin.json validation step (before the backup):
```bash
ORIGINAL_CURRENT_VERSION=$(jq -r '.version // empty' "$PLUGIN_JSON")
```

**Replace single-attempt logic with retry loop.** The collision/regression detection block (currently lines ~152–159) becomes the center of a `while` loop:

```
INITIAL_NEW_VERSION="$NEW_VERSION"
RETRY_COUNT=0
MAX_RETRIES=10

# Backup, rewrite, add
cp "$PLUGIN_JSON" "$BACKUP"
rewrite_plugin_json()  # jq + mv
git add "$PLUGIN_JSON"

while true; do
  git fetch origin main   # fail-closed on fetch error (no retry)
  ORIGIN_VERSION=$(git show origin/main:...)
  
  if same-version or regression:
    rollback_before_commit()
    
    if [[ RETRY_COUNT -ge MAX_RETRIES ]]; then
      fail "bump race: could not land after $MAX_RETRIES retries ..."
    fi
    
    BUMP_TYPE=$(_infer_bump_type "$ORIGINAL_CURRENT_VERSION" "$INITIAL_NEW_VERSION")
    NEW_VERSION=$(_apply_bump_type "$ORIGIN_VERSION" "$BUMP_TYPE")
    
    emit_breadcrumb "apply-bump: retry $((RETRY_COUNT+1))/$MAX_RETRIES — origin/main=$ORIGIN_VERSION, new attempt=$NEW_VERSION"
    
    RETRY_COUNT=$((RETRY_COUNT+1))
    cp "$PLUGIN_JSON" "$BACKUP"   # fresh backup for next rollback
    rewrite plugin.json to NEW_VERSION
    git add "$PLUGIN_JSON"
    continue
  fi
  break
done

git commit ...
```

**Important**: the `rewrite + git add` steps are duplicated inside the retry loop (once before the loop for the first attempt, once inside for retries). To keep the code DRY and avoid Bash 3.2 function-with-local issues, extract into a shell function `_rewrite_and_stage`.

**Bash 3.2 compatibility**: use arithmetic with `$((…))` only, no bash 4+ constructs.

### Test fixtures (scripts/test-apply-bump.sh)

The existing stub in `write_fake_git` needs to be extended to support a version-sequence file for multi-step collision tests. Add `STUB_ORIGIN_VERSION_SEQ_FILE` support: when the variable is set and the file exists, consume lines one at a time (head/tail pattern). When the file is exhausted, fall back to `STUB_ORIGIN_PLUGIN_JSON` or the default `{"version":"1.0.0"}`.

**Sub-test K: single collision then success**
- plugin.json = 1.0.0, --new-version 1.0.1 (PATCH)
- Fetch 1: ORIGIN=1.0.1 (collision) → retry 1 with 1.0.2
- Fetch 2: ORIGIN=1.0.0 (OK) → success at 1.0.2
- Assert: exit 0, APPLIED=true, version=1.0.2, 2 commits, 1 breadcrumb on stdout

**Sub-test L: multiple collisions then success**
- plugin.json = 1.0.0, --new-version 1.0.1 (PATCH)
- Fetch 1: ORIGIN=1.0.1 → retry 1 → 1.0.2
- Fetch 2: ORIGIN=1.0.2 → retry 2 → 1.0.3
- Fetch 3: ORIGIN=1.0.2 (stale) → success at 1.0.3
- Assert: exit 0, APPLIED=true, version=1.0.3, 2 commits, 2 breadcrumbs

**Sub-test M: cap exhaustion (11 fetch calls: initial + 10 retries all collide)**
- plugin.json = 1.0.0, --new-version 1.0.1
- Fetches 1-11 each return a version ≥ the attempted version
- Version sequence: 1.0.1, 1.0.2, ..., 1.0.11 (11 entries)
- After 10 retries (the 11th attempt), loud fail
- Assert: exit 1, APPLIED=false, ERROR contains "10 retries", version=1.0.0 (restored)

**Sub-test N: no collision baseline**
- plugin.json = 1.0.0, --new-version 1.0.1
- Fetch: ORIGIN=1.0.0 (lower) → success first try, no retry
- Assert: exit 0, APPLIED=true, version=1.0.1, no breadcrumb on stdout

**Sub-test O: breadcrumb shape**
- Same as sub-test K but capture stdout and verify breadcrumb format:
  `^apply-bump: retry 1/10 — origin/main=1\.0\.1, new attempt=1\.0\.2$`
- Run with LARCH_QUIET_DISABLE=1 (already set in harness)
- Assert: stdout contains one matching breadcrumb line


## Test plan
- `make test-apply-bump` must pass (all 5 new + existing tests green)
- `make lint` must pass (shellcheck, markdownlint, lint-bash32)
