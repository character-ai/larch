## Goal
Implement issue #2958: [IMPLEMENTING] [BUG] (URGENT) It seems that /upgrade-larch, instead of saving last 8 actually installed versions (when cleaning up), saves only last actual versions\n\nFor instance, let's say there are versions.

## Implementation Plan
## Plan

# Implementation Plan — Fix /upgrade-larch prune to keep last 8 mtime-ordered cache entries (Fixes #2958)

## Approach

The current prune in `upgrade-larch.sh` keeps the cache at <= 8 entries by sorting cache directory names in **semver ascending** order and evicting the lowest-numbered entry first. When `/upgrade-larch` later upgrades across a long version jump, this discards older-by-version-number cache entries even if those are the ones the user has actually been using.

Per Round 1 user resolution (`discussion-round1.md`), the fix:

1. Treats cache-directory **mtime** as the recency signal for retention. The 8 most-recently-touched cache directories are kept; the oldest-mtime entry is evicted first when the cache exceeds the cap.
2. Refreshes the executing plugin root's cache directory mtime on **session boot** via a shared helper called from `session-setup.sh` (canonical), `write-session-env.sh`, and `write-design-current-env.sh`. This propagates "actually used in recent sessions" into the recency signal so versions the user runs regularly stay protected from prune even when no session is live at `/upgrade-larch` time.
3. Introduces no new persistent state, no separate install-history file, no two-tier "installed vs. cached" model. "Installed == Present in Cache" — only the cache directory is consulted.

All existing protections stay in force: `LATEST_STABLE`, the currently-executing `PLUGIN_ROOT` basename, and active-session `LARCH_CLAUDE_PLUGIN_ROOT` pins (from `session-env.sh` scanning) are preserved regardless of mtime ranking. The "newer-than-`LATEST_STABLE`" auto-drop branch is preserved unchanged — it is orthogonal to the cap-trim ordering bug.

Cross-platform mtime extraction: GNU `stat -c '%Y'` is tried first (matches repo convention in `scripts/check-reviewers.sh`), then BSD `stat -f '%m'`. Output of each branch is validated against `^[0-9]+$` BEFORE acceptance so GNU's `-f` filesystem-info mode (which emits non-numeric text on Linux when fed an existing path) never feeds garbage into mtime sorting. If both branches fail or yield non-numeric output the mtime is treated as `0` so the entry sorts to the front (will be evicted first) — degrading gracefully toward "evict the entry we cannot rank" rather than masking the failure.

The sort pipeline uses `sort -k1,1n -k2,2` (numeric mtime ascending, then lexicographic version-name basename) so equal-mtime entries have a deterministic, portable tiebreaker without relying on GNU stable-sort or BSD `-s`.

## Files to modify/create

### NEW: `scripts/lib-larch-cache-touch.sh`

Tiny sourced library exposing one function:

```bash
# lib-larch-cache-touch.sh — shared helper for refreshing the executing larch
# plugin root's cache directory mtime so /upgrade-larch's mtime-based prune
# treats currently-used versions as recently-touched (Fixes #2958).
# Sourced (no shebang); does not set strict mode for the caller.

larch_touch_executing_cache_root() {
    # Args: --path <path> (defaults to $CLAUDE_PLUGIN_ROOT). Best-effort:
    # silently ignores filesystem errors. Refuses to touch paths whose
    # basename does not match the numeric-version grammar so the helper
    # cannot touch arbitrary operator-supplied paths.
    local path="${CLAUDE_PLUGIN_ROOT:-}"
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --path) path="${2:-}"; shift 2 ;;
            *) shift ;;
        esac
    done
    [[ -n "$path" ]] || return 0
    [[ -d "$path" ]] || return 0
    local base
    base=$(basename -- "$path")
    [[ "$base" =~ ^[0-9]+(\.[0-9]+)*$ ]] || return 0
    touch -c -- "$path" 2>/dev/null || true
    return 0
}
```

### NEW: `scripts/lib-larch-cache-touch.md`

Sibling stub naming this primary contract (per `.claude/rules/script-md-siblings.md`). Purpose: one-function shared library. Callers: `session-setup.sh`, `write-session-env.sh`, `write-design-current-env.sh`. Behavior: refresh mtime of `$CLAUDE_PLUGIN_ROOT` (or `--path`) when basename matches the numeric-version grammar; no-op otherwise; best-effort (silently ignores `touch` failures).

### UPDATED: `skills/upgrade-larch/scripts/upgrade-larch.sh`

- Add near `sort_versions()` / `list_cached_versions()`:

  ```bash
  stat_mtime() {
      # Cross-platform mtime extraction. Tries GNU stat -c first (matches
      # repo convention in scripts/check-reviewers.sh), then BSD stat -f.
      # Validates output as ^[0-9]+$ to reject GNU filesystem-info -f mode.
      # Echoes a non-negative integer; on total failure echoes 0 so the
      # caller can sort the entry to the front (= first eviction candidate).
      local file="$1"
      local mt
      if mt=$(stat -c '%Y' -- "$file" 2>/dev/null) && [[ "$mt" =~ ^[0-9]+$ ]]; then
          printf '%s\n' "$mt"
          return 0
      fi
      if mt=$(stat -f '%m' -- "$file" 2>/dev/null) && [[ "$mt" =~ ^[0-9]+$ ]]; then
          printf '%s\n' "$mt"
          return 0
      fi
      printf '0\n'
      return 0
  }

  list_cached_versions_by_mtime() {
      # Same input filter as list_cached_versions (numeric cache subdirs only),
      # but sorted ASCENDING by mtime (oldest first → first eviction candidate)
      # with lexicographic basename as the portable equal-mtime tiebreaker.
      local dirs=()
      local dir
      shopt -s nullglob
      dirs=("$LARCH_CACHE_DIR"/[0-9]*/)
      shopt -u nullglob

      for dir in "${dirs[@]}"; do
          [ -d "$dir" ] || continue
          local mt
          mt=$(stat_mtime "${dir%/}")
          printf '%s\t%s\n' "$mt" "$(basename "${dir%/}")"
      done | sort -k1,1n -k2,2 | cut -f2-
  }
  ```

- Inside the `if [ "$VERIFIED_TARGET" = true ]` prune block, replace the call site that populates `CACHED_VERSIONS`:

  ```diff
  -    while IFS= read -r version; do
  -        [ -n "$version" ] || continue
  -        CACHED_VERSIONS+=("$version")
  -    done < <(list_cached_versions)
  +    while IFS= read -r version; do
  +        [ -n "$version" ] || continue
  +        CACHED_VERSIONS+=("$version")
  +    done < <(list_cached_versions_by_mtime)
  ```

  No other prune-loop logic changes. The first loop (newer-than-`LATEST_STABLE`) is order-agnostic — it iterates all entries and removes every newer one (unless pinned). The cap-trim `while ... do for ...` loop iterates `SANITIZED_VERSIONS` from index 0; because `CACHED_VERSIONS` (and therefore `SANITIZED_VERSIONS`) is now mtime-asc with deterministic basename tiebreaker, the trim evicts the oldest-mtime unpinned entry first.

- Keep `list_cached_versions()` and `sort_versions()` intact for now (they may have other consumers; OOS cleanup can be filed separately if the validator flags dead code).

### UPDATED: `scripts/session-setup.sh`

- Near the top of the script (after argument parsing but before any work that depends on `CLAUDE_PLUGIN_ROOT`), source the new helper and call it:

  ```bash
  # Refresh the executing larch cache-directory mtime so /upgrade-larch's
  # mtime-based prune treats currently-used versions as recently-touched
  # (Fixes #2958). Best-effort; helper silently no-ops on non-numeric paths.
  # shellcheck source=scripts/lib-larch-cache-touch.sh
  source "$SCRIPT_DIR/lib-larch-cache-touch.sh"
  larch_touch_executing_cache_root
  ```

  Placement: AFTER `SCRIPT_DIR` is established and BEFORE the working-tree / repo / reviewer probe blocks (those don't depend on the touch, but doing it early ensures the executing version is refreshed on every session-setup invocation regardless of which downstream branch runs).

### UPDATED: `scripts/write-session-env.sh`

- After the existing `CLAUDE_PLUGIN_ROOT_VALUE` validation block (the `if [[ -n "$CLAUDE_PLUGIN_ROOT_VALUE" ]]` regex / absolute-path validation around lines 136-145), source and invoke the shared helper:

  ```bash
  # Refresh executing larch cache-directory mtime (Fixes #2958) AFTER validation
  # so a touch never happens on inputs the writer would reject.
  # shellcheck source=scripts/lib-larch-cache-touch.sh
  source "$SCRIPT_DIR/lib-larch-cache-touch.sh"
  larch_touch_executing_cache_root --path "$CLAUDE_PLUGIN_ROOT_VALUE"
  ```

  Defense in depth: `session-setup.sh` already touches via the helper on each session boot; this call ensures the executing version is refreshed any time `write-session-env.sh` runs directly (e.g., nested skill invocations that bypass the full setup path).

### UPDATED: `scripts/write-design-current-env.sh`

- After the `CLAUDE_PLUGIN_ROOT_VALUE` validation analogous to `write-session-env.sh`, source the helper and call it the same way:

  ```bash
  # Refresh executing larch cache-directory mtime (Fixes #2958).
  # shellcheck source=scripts/lib-larch-cache-touch.sh
  source "$(dirname "$0")/lib-larch-cache-touch.sh"
  larch_touch_executing_cache_root --path "$CLAUDE_PLUGIN_ROOT_VALUE"
  ```

  Same rationale as `write-session-env.sh` — covers the `/design` writer path that does not call `write-session-env.sh`.

### UPDATED: `skills/upgrade-larch/scripts/upgrade-larch.md`

- Step 8 currently says: "It first removes cached numeric version directories that are newer than `LATEST_STABLE`, then keeps at most 8 cached versions total while preserving the verified stable directory."
- Replace with: "It first removes cached numeric version directories that are newer than `LATEST_STABLE`, then keeps at most 8 cached versions total by mtime — evicting the oldest-mtime entry first with lexicographic version-basename as the deterministic equal-mtime tiebreaker — while preserving the verified stable directory."
- Add a new sentence after the existing session-pin preservation paragraph: "Mtime ordering replaces the legacy semver-ascending trim order. `scripts/session-setup.sh`, `scripts/write-session-env.sh`, and `scripts/write-design-current-env.sh` each call the shared helper `scripts/lib-larch-cache-touch.sh` so versions the user actively runs stay current and are protected from prune even when no session is live at `/upgrade-larch` time."
- Append `scripts/session-setup.sh`, `scripts/write-session-env.sh`, `scripts/write-design-current-env.sh`, and `scripts/lib-larch-cache-touch.sh` to the Edit-in-sync list.

### UPDATED: `scripts/write-session-env.md`

- Add to the behavior section: "When `CLAUDE_PLUGIN_ROOT` is set and validates, the script also invokes `larch_touch_executing_cache_root` from `scripts/lib-larch-cache-touch.sh` (best-effort) so the corresponding larch cache directory's mtime reflects the most recent session start. This is consumed by `skills/upgrade-larch/scripts/upgrade-larch.sh`'s mtime-based prune (Fixes #2958)."
- Add `skills/upgrade-larch/scripts/upgrade-larch.sh` and `scripts/lib-larch-cache-touch.sh` to the consumer list.

### UPDATED: `scripts/write-design-current-env.md`

- Add the same behavior paragraph as `write-session-env.md` (parallel call site, parallel rationale).

### UPDATED: `scripts/session-setup.md`

- Add to the behavior section: "Sources `scripts/lib-larch-cache-touch.sh` and invokes `larch_touch_executing_cache_root` (best-effort) on every invocation so the executing larch cache root mtime is refreshed once per session boot — consumed by `skills/upgrade-larch/scripts/upgrade-larch.sh`'s mtime-based prune (Fixes #2958)."

### UPDATED: `SECURITY.md`

- Add a subsection adjacent to the existing "Plugin-root rehydration" / session-env trust paragraphs:
  - State that `larch_touch_executing_cache_root` is a best-effort, no-source, no-eval filesystem operation whose only effect is updating an existing directory's mtime via `touch -c`.
  - Document the numeric-basename grammar guard `^[0-9]+(\.[0-9]+)*$` that prevents touching arbitrary operator-supplied paths.
  - State the trust model: mtime is a same-UID local signal; another user on the same host cannot influence the cache prune by touching directories owned by this user (the existing `list_cached_versions` glob already lives under the user-owned cache root).
  - Document failure behavior: read-only filesystem or permission-denied is silently tolerated; the writer / session-setup never fails because of touch.

### UPDATED: `docs/installation-and-setup.md`

- In the "Upgrading larch" section (or wherever the Upgrade flow / cache behavior is described): replace any "last 8 versions" wording with: "`/upgrade-larch` keeps the 8 most-recently-touched cache directories. The mtime is refreshed whenever a Claude session starts using that version, so versions you continue to run remain protected from prune even when no session is live at `/upgrade-larch` time."

### UPDATED: `skills/upgrade-larch/scripts/test-upgrade-larch-prune.sh`

- **Add a `write_stub_stat` helper** parallel to `write_stub_rm`:

  ```bash
  write_stub_stat() {
      local path="$1"
      cat > "$path" <<'EOF'
  #!/usr/bin/env bash
  set -euo pipefail
  target="${*: -1}"
  if [[ -n "${STAT_FAIL_VERSION:-}" && "$target" == */"$STAT_FAIL_VERSION" ]]; then
      # Fail BOTH the -c and -f probes for this specific version.
      for arg in "$@"; do
          case "$arg" in -c|-f) exit 1 ;; esac
      done
  fi
  /usr/bin/stat "$@"
  EOF
      chmod +x "$path"
  }
  ```

  Wire it in `run_case` alongside `write_stub_rm` and pass `STAT_FAIL_VERSION="${STAT_FAIL_VERSION:-}"` through the SCRIPT environment.

- **Update existing cases to use explicit `touch -t` mtime seeding**:
  - `cap-prune-trims-to-eight`, `multi-pinned-oldest-still-trims-to-eight`, `cap-prune-rm-failure-skips-retry` — after the `for version in ${CACHED_VERSIONS:-}; do mkdir -p "$cache_root/$version"; done` block, append a deterministic mtime seed (one second per version, ascending in version order so existing assertions about eviction outcomes remain correct):

    ```bash
    _seed_idx=0
    for version in ${CACHED_VERSIONS:-}; do
        _seed_idx=$((_seed_idx + 1))
        printf -v _ts '20%02d01010001' "$((10 + _seed_idx))"  # 2010..., 2011..., 2012... in order
        touch -t "$_ts" -- "$cache_root/$version"
    done
    ```

    For cases that need mtime to DIFFER from version-asc order (the new ones below), seed mtime explicitly per case AFTER this default seed loop.

- **Add new mtime-specific cases**:
  - **`mtime-asc-evicts-oldest-touched`** — install target `42.0.10`, `GH_OUTPUT=$'42.0.10\n'`, `INSTALL_RESULT_VERSION=42.0.10`, `INITIAL_INSTALLED_VERSION=42.0.5`, `PLUGIN_ROOT_VERSION=42.0.5`, cache `42.0.1 42.0.2 42.0.3 42.0.4 42.0.5 42.0.6 42.0.7 42.0.8 42.0.9`. After the default mtime seed, **override**: `touch -t 200001010001 -- "$cache_root/42.0.9"` (newest version → oldest mtime) and `touch -t 209901010001 -- "$cache_root/42.0.1"` (oldest version → newest mtime among non-install entries). Assert post-prune cache contains `42.0.1 42.0.10` and selectively others, but specifically that `42.0.9` is evicted and `42.0.1` is retained. This demonstrates mtime ordering wins over semver ordering. Since all initial cache entries are <= `LATEST_STABLE=42.0.10`, the newer-than-stable pre-prune does not interfere (FINDING_4 resolution).
  - **`mtime-tiebreaker-lexicographic-basename`** — install target `42.1.0` with cache `42.0.8 42.0.9`. After default seed, set both to the same mtime: `touch -t 209901010001 -- "$cache_root/42.0.8" "$cache_root/42.0.9"`. Cap=8 will keep both (cache count <= 8) — assert both retained. Then add a 9th entry `42.0.7` with the same mtime: now cap=8 must evict one. With `sort -k1,1n -k2,2`, the lexicographic tiebreaker evicts `42.0.7` (earliest in lex order). Assert: `42.0.7` evicted, `42.0.8` and `42.0.9` retained.
  - **`stat-fallback-mtime-zero`** — install target `42.0.10` with cache `42.0.1..42.0.9`. After default seed, set `STAT_FAIL_VERSION=42.0.5`. Assert that `42.0.5` is evicted first (mtime=0 sorts to front) without script crash, regardless of its actual filesystem mtime.

- Document the three new cases plus the `write_stub_stat` wiring in the harness header comment.

### UPDATED: `skills/upgrade-larch/scripts/test-upgrade-larch-prune.md`

- Add a "Mtime-based prune coverage" subsection naming the new cases and the cross-platform `stat` fallback expectation.
- Note that existing cases now use explicit `touch -t` seeding for deterministic mtimes (removes the dependence on `mkdir`-time creation order).
- Document the `STAT_FAIL_VERSION` environment knob and the `write_stub_stat` PATH-shim pattern.

### UPDATED: `scripts/test-session-env-roundtrip.sh`

- Add a new section (labeled `F` to follow the existing `A`-`E` enumeration in the file header comments) that:
  - Creates a fake larch cache parent dir with a numeric-version subdir (e.g., `tmp/cache/42.5.36`).
  - Sets the subdir's mtime to a known-old value: `touch -t 200001010001 -- "<dir>"`.
  - Invokes `write-session-env.sh` with `CLAUDE_PLUGIN_ROOT=<that subdir>`.
  - Asserts the subdir's post-invocation mtime is strictly greater than the seeded old mtime.
  - Adds a negative case: `CLAUDE_PLUGIN_ROOT` whose basename does NOT match the numeric grammar (e.g., `/tmp/cache/dev-checkout`). Assert that no `touch` happens (mtime unchanged).
- Reuse the existing `WRITE_SCRIPT` constant and the temp-dir scaffolding pattern from sections A-E.

### UPDATED: `scripts/test-session-env-roundtrip.md`

- Document new section F (mtime touch behavior) with its two sub-assertions: touch on numeric basename refreshes mtime; no-op on non-numeric basename leaves mtime unchanged.

## Edge cases

- **Mtime resolution = 1 second** on most filesystems. Two cache dirs touched in the same second sort by the lexicographic basename tiebreaker (`sort -k1,1n -k2,2`), producing a deterministic, portable order across macOS and Linux.
- **Clock skew / mtime in the future**: a cache dir whose mtime is in the future (e.g., from a build host with a wrong clock) sorts as "newest" → preserved. Operationally indistinguishable from "actually recent", which is acceptable.
- **Cache dir created during /upgrade-larch but uninstalled before verified install**: should not happen because `claude plugin install` runs before the prune block; if it does, the dir has fresh mtime and gets preserved (false positive, but the next /upgrade-larch will evict it once it ages out).
- **`stat` returns empty string or unexpected output** (e.g., GNU stat's `-f` filesystem-info mode emitting prose): `stat_mtime` validates against `^[0-9]+$` and falls through to the second branch on validation failure. On total failure it returns `0`, sorting the entry to the front (evict first). This is fail-safe: we cannot rank → we treat as least-recent.
- **`touch -c` fails on read-only filesystem in any session writer**: silently ignored via `|| true` inside the shared helper. The session-env file write proceeds normally. Subsequent `/upgrade-larch` runs will see the stale mtime and may evict that version — a degraded but consistent outcome on read-only mounts.
- **Non-numeric basename for `CLAUDE_PLUGIN_ROOT`** (e.g., developer running `claude --plugin-dir /repos/larch-dev`): the helper's regex guard skips the touch; no false-positive touches of non-cache paths.
- **Cache parent dir = `/`** (would only happen with a malformed `PLUGIN_ROOT`): `list_cached_versions_by_mtime` only matches `[0-9]*/` glob entries under `$LARCH_CACHE_DIR`; an absurd parent would either yield zero matches or only legitimate numeric-version dirs, so no broader paths are touched.

## Failure modes

1. **Cross-platform `stat` divergence**: a host where neither `stat -c '%Y'` nor `stat -f '%m'` works (highly unusual; may occur on minimal busybox systems). Earliest signal: `stat-fallback-mtime-zero` test fails on that platform; or in production, the warning is implicit — every dir gets mtime=0 and the cap-trim eviction order becomes lexicographic-only (the tiebreaker is still deterministic). Mitigation: document the macOS / Linux assumption in `upgrade-larch.md` and `SECURITY.md`; the lexicographic tiebreaker prevents arbitrary churn.
2. **Mtime ordering disagrees with operator intuition**: a user who manually `rsync`s their cache between machines can shuffle mtimes such that "the version I want to keep" gets the oldest mtime. Earliest signal: surprising prune output (cached version disappeared after /upgrade-larch). Mitigation: the existing active-session pin path (write a stub `session-env.sh` under `LARCH_SESSIONS_DIR`) is the documented escape hatch for "always keep this version".
3. **Per-cache-dir touch races with concurrent /upgrade-larch**: two `claude plugin install` invocations running concurrently could both touch the same dir; outcome is idempotent (mtime ends up "now-ish"). No corruption. Earliest signal: none — the operation is safe.

## Testing strategy

- Run the existing `make lint-bash32` after edits to verify Bash 3.2 portability of the new helpers (`stat_mtime`, `list_cached_versions_by_mtime`, `larch_touch_executing_cache_root`, the touch call sites). None of the new code uses Bash 4+ features.
- Run `bash skills/upgrade-larch/scripts/test-upgrade-larch.sh` and `bash skills/upgrade-larch/scripts/test-upgrade-larch-prune.sh` to confirm existing coverage passes and the new cases (`mtime-asc-evicts-oldest-touched`, `mtime-tiebreaker-lexicographic-basename`, `stat-fallback-mtime-zero`) run green.
- Run `bash scripts/test-session-env-roundtrip.sh` to confirm the new touch hook fires only for numeric-basename `CLAUDE_PLUGIN_ROOT` values.
- Run `bash scripts/relevant-checks.sh` (the project-standard pre-commit aggregator) on the final tree.
- Manual smoke test in a real cache: `touch -t 200001010000 ~/.claude/plugins/cache/larch-local/larch/<oldest-version>`, then run `/upgrade-larch` — verify the seeded-old version is the first to be evicted when the cache exceeds 8 entries.

diff_lines: 320


## Acceptance

- `/upgrade-larch` retains cached versions by mtime, not version-number order; the oldest-mtime entry is evicted first when the cache exceeds 8.
- Cache-directory mtime is refreshed on session boot via the shared `larch_touch_executing_cache_root` helper, invoked from `session-setup.sh`, `write-session-env.sh`, and `write-design-current-env.sh`.
- `stat_mtime` uses GNU `stat -c '%Y'` first, then BSD `stat -f '%m'`, validating each branch's output against `^[0-9]+$` before acceptance.
- Equal-mtime entries break ties deterministically via `sort -k1,1n -k2,2` (lexicographic version-basename).
- Existing pin protections (LATEST_STABLE, executing PLUGIN_ROOT basename, active-session pins) remain in force.
- `SECURITY.md` and `docs/installation-and-setup.md` document the new retention semantics.
- `test-upgrade-larch-prune.sh` covers three new cases: `mtime-asc-evicts-oldest-touched`, `mtime-tiebreaker-lexicographic-basename`, `stat-fallback-mtime-zero`. Existing cases use explicit `touch -t` mtime seeding.
- `test-session-env-roundtrip.sh` covers section F: numeric-basename touch refreshes mtime, non-numeric basename is no-op.
- `make lint-bash32` passes; both `test-upgrade-larch*.sh` harnesses pass; `relevant-checks.sh` passes.

diff_lines: 320

## Test plan
(no test plan section in plan-file)
