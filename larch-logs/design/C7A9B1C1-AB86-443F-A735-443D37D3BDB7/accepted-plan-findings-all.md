### FINDING_1: SessionStart fail-open capture missing under `set -e`
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-dyn-hook-fail-open
- **Severity**: blocking
- **Concern**: The plan replaces the sourced `resolve_implement_tmpdir` call with bare `IMPLEMENT_TMPDIR=$(python3 … session resolve-implement-tmpdir …)` but does not require the existing `|| IMPLEMENT_TMPDIR=""` fail-open guard. Under `set -euo pipefail`, a non-zero CLI exit inside command substitution aborts `scripts/sessionstart-health.sh` before `exit 0`, breaking the SessionStart always-exit-0 / non-blocking contract and suppressing unrelated advisories (dirty tree, stalled-run, sparse-cone).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In `scripts/sessionstart-health.sh`, mirror the current fail-open capture: `IMPLEMENT_TMPDIR=$(python3 "$PLUGIN_ROOT/python/cli.py" session resolve-implement-tmpdir --cwd "$HOOK_CWD" 2>/dev/null) || IMPLEMENT_TMPDIR=""`. Document the same pattern in `scripts/sessionstart-health.md`.
  - From Cursor-Innovation: In the `### UPDATED: scripts/sessionstart-health.sh` section, require the same pattern as today: `IMPLEMENT_TMPDIR=$(python3 "$PLUGIN_ROOT/python/cli.py" session resolve-implement-tmpdir --cwd "$HOOK_CWD" 2>/dev/null) || IMPLEMENT_TMPDIR=""` (or equivalent `|| true` before assignment). Do not rely on "non-zero resolves empty" prose alone.
  - From Cursor-Pragmatic: In `scripts/sessionstart-health.sh`, spell out the same fail-open capture as today: `IMPLEMENT_TMPDIR=$(python3 "$PLUGIN_ROOT/python/cli.py" session resolve-implement-tmpdir --cwd "$HOOK_CWD" 2>/dev/null) || IMPLEMENT_TMPDIR=""`
  - From Cursor-dyn-hook-fail-open: Add an explicit hook requirement: IMPLEMENT_TMPDIR=$(python3 "$PLUGIN_ROOT/python/cli.py" session resolve-implement-tmpdir --cwd "$HOOK_CWD" 2>/dev/null) || IMPLEMENT_TMPDIR="" (or equivalent set +e wrapper) in scripts/sessionstart-health.sh and document it in scripts/sessionstart-health.md


### FINDING_2: No-spawn regression not observable when no session dirs exist
- **Reviewer(s)**: Codex-Arch, Codex-Pragmatic, Codex-Requirements, Codex-dyn-hook-fail-open
- **Severity**: important
- **Concern**: The planned SessionStart test only uses a failing `python3` stub when no `claude-implement-*` dirs exist. A hook that wrongly invokes `python3` and then fail-opens to empty stdout still passes, so the pre-check / no-spawn contract can regress without test failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Make the python3 stub record invocation or emit a unique token, then assert the marker or token is absent when no session dirs exist
  - From Codex-Pragmatic: Make the stub write a marker or counter and assert it is absent, or add a structural check that the claude-implement-* pre-check occurs before the python3 CLI call
  - From Codex-Requirements: Make the stub write a marker or counter and assert it is absent, or add a structural check that the claude-implement-* pre-check occurs before the python3 CLI call
  - From Codex-dyn-hook-fail-open: Make the stub write a marker or counter and assert it is absent, or add a structural check that the claude-implement-* pre-check occurs before the python3 CLI call


### FINDING_3: Fail-open path untested when pre-check passes and resolver exits non-zero
- **Reviewer(s)**: Codex-Innovation, Codex-dyn-resolver-parity
- **Severity**: important
- **Concern**: The test plan does not exercise the branch where a `claude-implement-*` dir exists (pre-check passes) and `python3` exits non-zero. Under `set -e`, a bare command-substitution bug would make SessionStart exit non-zero on stale session dirs; the no-dir-only failing stub never catches this.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Split this into two minimal cases: no session dirs with a marker stub and an assertion that python3 was not invoked, plus one dummy claude-implement-* dir with a failing python3 stub asserting rc 0 and empty stdout.
  - From Codex-dyn-resolver-parity: Add one test case in scripts/test-sessionstart-health.sh with a claude-implement-* dir and a python3 stub that exits non-zero; assert rc 0 and no advisory.


### FINDING_4: Bash pre-check session-root formula underspecified
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: Hook pre-check sections say "scan the same three roots" but do not pin the exact path formula the bash lib uses. A hand-rolled pre-check that omits `XDG_CACHE_HOME` or `${HOME:-/tmp}` can skip `python3` while eligible `claude-implement-*` dirs exist only under the cache root, causing boundary advisories (and Stop blocking) to silently fail open with no test failure on the skip path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: In both hook update sections, spell out the identical three-root bash loop (or a tiny shared inline snippet) using `${XDG_CACHE_HOME:-${HOME:-/tmp}/.cache}/larch/sessions`, `/tmp`, and `/private/tmp`. In `python/session_env.py`, build the cache root via existing `cleanup_cache_sessions_root()` rather than re-encoding the formula.
  - From Cursor-Pragmatic: In both hook sections, pin the exact first-root expansion to match `implement_session_roots()` (`${XDG_CACHE_HOME:-${HOME:-/tmp}/.cache}/larch/sessions`, then `/tmp`, then `/private/tmp`) and add a harness case that sets only `XDG_CACHE_HOME` (as `scripts/test-sessionstart-health.sh` already does)


### FINDING_7: Resolver parity tests omit keepalive `=` and TTL-equality edge cases
- **Reviewer(s)**: Codex-dyn-resolver-parity
- **Severity**: important
- **Concern**: The plan states bash preserves everything after the first `=` in keepalive values and treats age exactly equal to TTL as stale, but the proposed `python/test_session_env.py` coverage list does not require either assertion. A Python port using the wrong split or `>` instead of `>=` could pass planned tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-resolver-parity: Add proportionate resolver tests for a CLONE_PATH containing `=` and for age exactly equal to LARCH_IMPLEMENT_TMPDIR_TTL_SECONDS being rejected.


### FINDING_8: `agent-lint.toml` Makefile-only comment cites deleted harness paths
- **Reviewer(s)**: Cursor-dyn-retirement-surface
- **Severity**: important
- **Concern**: The retirement plan drops four allowlist strings but not the Makefile-only comment block that still cites deleted harness paths. After those paths land in `python/migrated-scripts.tsv`, `make lint-retired-scripts` fails on `agent-lint.toml` even when hooks and docs are clean.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-retirement-surface: In `### UPDATED: agent-lint.toml`, also delete or rewrite the comment lines at 1123-1124 (Makefile-only harness note) when removing the `test-resolve-implement-tmpdir` allowlist entries




### FINDING_3:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: <TMPDIR>/plan.txt:136-139
- **Concern**: [SCOPE-REDUCTION] Marker-based no-session-dir SessionStart test depends on global /tmp and /private/tmp being empty. Scenario: The planned hook pre-check scans fixed roots including /tmp and /private/tmp, so an unrelated stale claude-implement-* directory can invoke the python3 stub and fail make lint even when the test-created cache root has no sessions
- **Proposed resolution**: Replace the marker-based runtime case with a structural no-spawn assertion that does not depend on ambient global tmp state, and keep the resolver-fail runtime case for fail-open coverage


