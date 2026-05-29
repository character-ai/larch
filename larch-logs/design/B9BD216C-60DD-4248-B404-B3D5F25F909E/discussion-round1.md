## Decision 1: "Last 8 installed" detection mechanism
- **Question**: How should /upgrade-larch determine the most-recently-installed versions for retention ordering?
- **Resolution**: Write a per-version install-stamp file (e.g. `.larch-installed-at` holding epoch seconds) at install time; sort version dirs by it. Robust and cross-platform; survives a revert TO an older version. Pre-existing un-stamped dirs fall back to directory mtime for ordering (migration detail resolved in the plan).
- **Source**: user

## Decision 2: Identity record for /implement hook routing
- **Question**: The prune's active-protection role is removed, but lib-resolve-implement-tmpdir.sh still needs (CLONE_PATH, SESSION_ID). How should that payload survive?
- **Resolution**: Rename `.larch-keepalive` to a slim, honestly-named `.larch-session` (2 fields: CLONE_PATH, SESSION_ID), drop the protection framing, and repoint the two readers (`lib-resolve-implement-tmpdir.sh`, `hook-stop-fail-close.sh`). Every session keeps writing it at boot.
- **Source**: user

## Decision 3: Version-dir activity touch
- **Question**: Keep the lib-larch-cache-touch.sh mtime-touch on the executing version dir?
- **Resolution**: Drop it. Remove `scripts/lib-larch-cache-touch.sh` and all three call sites (session-setup.sh, write-session-env.sh, write-design-current-env.sh). With install-stamp ordering and "keep the 8 newest installs," version-dir mtime is irrelevant to retention, so the touch has no remaining purpose.
- **Source**: user

## Decision 4: Stage A (delete-newer-than-stable)
- **Question**: Keep Stage A's special-case that deletes any cached version newer than the verified stable?
- **Resolution**: Drop it. Let the unified retention rule govern all versions; a recently-installed newer-than-stable version becomes a valid rollback target instead of being force-deleted.
- **Source**: user

## Decision 5: Retention window value
- **Question**: What age window should /cleanup session-dir reaping use, and should it be env-overridable?
- **Resolution**: 7 days, overridable via env var. Applies to /cleanup session dirs only (see Decision 6).
- **Source**: user

## Decision 6: Retention semantics — 8 is a MAXIMUM (cap), not a floor
- **Question**: Is 8 a floor (keep at least 8, cache grows velocity-bound) or a maximum (cap)? Can the 7-day window delete a version that is among the 8 most-recently-installed?
- **Resolution**: 8 is a hard MAXIMUM. /upgrade-larch keeps exactly the 8 most-recently-installed version dirs (install-stamp order) and deletes everything beyond the 8 newest. The 7-day window does NOT delete any of the 8-newest version dirs — it governs /cleanup session dirs only. Cache size = min(8, total version dirs). The just-installed target is always newest and always kept. This reverses the issue body's "floor / no upper cap" proposal.
- **Source**: user

## Decision 7: Prune location
- **Question**: Should version-dir pruning stay in /upgrade-larch or move into an age-based /cleanup?
- **Resolution**: Keep in /upgrade-larch (runs after a verified install). /cleanup handles session dirs and dangling design-env symlinks only.
- **Source**: user

## Constraint A: current-design-env-*.sh is load-bearing
- **Question**: Can the current-design-env-*.sh symlinks be removed?
- **Resolution**: No. They are sourced by the /design rehydration prelude at the top of every Bash block. Leave the mechanism untouched. /cleanup already ignores them (symlink, not dir); optionally reap only DANGLING ones.
- **Source**: codebase (skills/design/SKILL.md prelude) + issue load-bearing dependency #2

## Constraint B: (CLONE_PATH, SESSION_ID) binding must not break hook routing
- **Question**: What exactly does lib-resolve-implement-tmpdir.sh require?
- **Resolution**: It matches keepalive `CLONE_PATH` against the hook cwd and (when LARCH_TOKEN_SESSION_ID is set) requires an exact `SESSION_ID` match; CLONE_PATH lives ONLY in the keepalive file today (SESSION_ID is also duplicated in a per-dir `session-id` file). The renamed `.larch-session` must preserve both fields and the resolver/hook readers must be repointed atomically with the writer.
- **Source**: codebase (skills/implement/scripts/lib-resolve-implement-tmpdir.sh, hook-stop-fail-close.sh)

## Constraint C: /cleanup newest-activity keying
- **Question**: How is a session dir's "age" measured?
- **Resolution**: newest-activity = max(mtime of the dir AND its immediate children), not the dir's own mtime alone (APFS does not bump parent-dir mtime on child content edits). Already agreed by the requester.
- **Source**: issue ("Agreed decision")

## Constraint D: portability + quiet-stream
- **Question**: Any cross-cutting invariants the edits must preserve?
- **Resolution**: Bash 3.2 compatibility (no associative arrays/namerefs/mapfile/${var^^}) and the lib-quiet.sh FD-3 contract must be preserved in all touched scripts. Each touched .sh keeps its sibling .md in sync; affected test-*.sh harnesses and Makefile targets stay wired.
- **Source**: AGENTS.md / BASH_AUTHORING.md / .claude/rules

Decisions resolved: 7 (user) + 4 codebase/issue constraints recorded.
