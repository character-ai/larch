# Discussion Round 1 — issue #6108 (bg-poll-guard cross-clone block)

## Decision 1: Marker-read exemption scope
- **Question**: Should the diagnosability exemption cover only reads of `.bg-wait-active` marker files, or also `.completed/*` sentinels?
- **Resolution**: Marker file only. Exempt Bash/Read of paths whose basename is `.bg-wait-active`, including same-clone. `.completed/*` sentinel probes stay guarded; they are the polling shape the guard exists to deny and already have the sanctioned one-probe recovery path plus clamp.
- **Source**: user (AskUserQuestion timed out; recommended option accepted per terse-answer rule)

## Decision 2: sessionstart-health version-skew check
- **Question**: Is the optional `sessionstart-health.sh` comparison of the session's pinned plugin root vs `installed_plugins.json` in scope?
- **Resolution**: Deferred to an OOS follow-up issue. This PR ships the hook's plugin version in every deny reason plus a docs note that guard-hook fixes reach only sessions started after upgrade.
- **Source**: user (AskUserQuestion timed out; recommended option accepted per terse-answer rule)

## Decision 3: Clone-ownership mechanism and helper placement
- **Question**: Which ownership signal gates marker collection, and where does the helper live?
- **Resolution**: Use the `.larch-keepalive` `CLONE_PATH` comparison (`marker_foreign_clone()` + `clone_paths_same()`, #5927), duplicated into `scripts/hook-bg-poll-guard.sh`. Hooks stay self-contained per `BASH_AUTHORING.md`; `hook-no-progress-guard.sh` already duplicates `marker_candidates()` with a "same discovery logic" comment, so duplication is the established pattern. `_write_session_identity()` (`python/larch/state/session_env.py:1508`) writes `.larch-keepalive` with `CLONE_PATH` into every design/implement session dir at setup.
- **Source**: codebase

## Decision 4: Fail-safe semantics for uncorrelatable input
- **Question**: When hook-input `cwd` is empty or the keepalive is missing/unparsable, does collection-time filtering drop markers (guard disabled) or keep them?
- **Resolution**: Keep them. `marker_foreign_clone()` returns "foreign" only when both the current cwd and the marker's `CLONE_PATH` are known and canonically differ; any uncertainty keeps the marker, so the guard is never disabled by filtering. Same #5927 semantics. Cross-clone denials can persist only in the rare empty-cwd case, and downstream per-branch plausibility gates still apply there.
- **Source**: codebase

## Decision 5: No sanctioned cross-clone coordination exists
- **Question**: Does any legitimate flow inspect another clone's live session dir that collection-time filtering would newly allow?
- **Resolution**: None found in skills, scripts, or shared references. Newly allowing foreign-dir reads breaks no sanctioned deny expectation.
- **Source**: codebase

## Decision 6: Hard constraints
- **Question**: What must not break?
- **Resolution**: Same-clone denials must keep firing (guard's core purpose, regression tests exist). Deny JSON stays static-printf, never jq (#5610). Hook keeps fail-open posture on malformed input. Bash 3.2 portability per `BASH_AUTHORING.md`. Sibling `.md` contract docs update in the same PR.
- **Source**: codebase
