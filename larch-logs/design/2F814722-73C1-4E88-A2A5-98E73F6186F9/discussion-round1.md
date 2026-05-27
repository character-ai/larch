## Decision 1: Definition of "installed"
- **Question**: What counts as an "installed" larch version for the purpose of cache retention?
- **Resolution**: "Installed == Present in Cache". No separate install-event tracking, no persistent history file. The cache directory state (mtime) is the only recency signal the design needs.
- **Source**: user

## Decision 2: Prune eviction order when cache exceeds 8 entries
- **Question**: When the cache count exceeds the cap of 8, which entries should be pruned first?
- **Resolution**: By cache-directory mtime ascending — drop the oldest mtime first, keep the 8 most-recently-touched cache directories. LATEST_STABLE, executing-root, and active-session pins remain protected regardless.
- **Source**: user

## Decision 3: Cache mtime refresh on session boot
- **Question**: Should starting a Claude session also refresh the mtime of the executing cache directory, so versions used in recent sessions stay protected even when no session is live at /upgrade-larch time?
- **Resolution**: Yes — session boot must touch the cache directory of the executing plugin root. This makes the new mtime ordering match the user's "actually installed and used" intuition.
- **Source**: user

## Decision 4: Cap value
- **Question**: Should the cap of 8 stay, or change?
- **Resolution**: Stay at 8 — explicitly named "last 8 installed" in the issue. No alternative requested.
- **Source**: user (issue body)

## Decision 5: Preserve "newer than LATEST_STABLE" auto-prune
- **Question**: The current script also drops cache entries with version numbers greater than LATEST_STABLE (rollback-prevention path), independent of the cap. Should that stay?
- **Resolution**: Keep it as-is. Orthogonal to the eviction-order bug; protects users from accidentally inheriting pre-release / draft / yanked versions.
- **Source**: codebase (existing behavior — `version_gt "$version" "$LATEST_STABLE"` branch in upgrade-larch.sh)

## Decision 6: Active-session / executing-root / LATEST_STABLE pinning
- **Question**: Should the existing pin logic (active session-env.sh, current PLUGIN_ROOT basename, LATEST_STABLE) continue to protect cache entries from prune?
- **Resolution**: Yes — keep all current pin protections. They are non-negotiable safety nets for in-flight sessions and rollback candidates. mtime ordering is an additional eviction signal layered ON TOP of these pins.
- **Source**: codebase (existing behavior — multiple guards in upgrade-larch.sh prune loop)

## Decision 7: Hard constraint — regression harness
- **Question**: How should the existing `test-upgrade-larch-prune.sh` cases be reconciled with the new ordering?
- **Resolution**: Existing case fixtures whose expected outcomes assumed version-asc trim must be updated to seed deterministic mtimes (e.g., `touch -t` on cache directories) so the cases still describe meaningful retention scenarios under mtime ordering. New cases must cover: (a) downgrade scenario where mtime != version order, (b) session-boot mtime-touch path, (c) idempotency (mtime stable across `/upgrade-larch` runs that don't change install state).
- **Source**: codebase (existing tests at `skills/upgrade-larch/scripts/test-upgrade-larch-prune.sh`)

## Decision 8: Non-goal — "installed history" persistence
- **Question**: Should we add a persistent `~/.cache/larch/installed-history.txt` or similar log of install events?
- **Resolution**: No — out of scope. User explicitly equated "Installed" with "Present in Cache". The fix is purely about ordering and mtime hygiene; no new persistent state.
- **Source**: user

## Decision 9: Non-goal — change cache population semantics
- **Question**: Should the design also change what gets put INTO the cache (e.g., prevent marketplace from caching non-installed versions)?
- **Resolution**: No — the cache is populated by `claude plugin install` (Claude Code internals); /upgrade-larch only manages prune. Out of scope.
- **Source**: user (issue scoped to /upgrade-larch behavior)
