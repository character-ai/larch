## Plan

## Approach

- Treat `approach-synthesis.txt` as `NO_SKETCHES`.
- Follow the approved outline and discussion constraints.
- Keep hooks in bash.
- Add only a gated Python CLI resolver.
- Preserve resolver behavior exactly.
- Pin the bash pre-check root formula to the existing lib literal so hooks and Python stay aligned.
- Require explicit `set -e`-safe fail-open capture in SessionStart; keep Stop hook fail-open when calling Python.

## Files to modify/create

### UPDATED: python/session_env.py

Add an importable resolver near the session-root helpers:

- `implement_session_roots(*, env: Mapping[str, str] | None = None) -> tuple[Path, ...]` (or private equivalent):
  - First root: `cleanup_cache_sessions_root()` using the passed `env` (or `os.environ`) so the cache path matches `${XDG_CACHE_HOME:-${HOME:-/tmp}/.cache}/larch/sessions` and the `HOME`-unset `/tmp/.cache/larch/sessions` fallback.
  - Then `/tmp`.
  - Then `/private/tmp`.
  - Do not re-encode the cache formula outside `cleanup_cache_sessions_root()`.
- `resolve_implement_tmpdir(hook_cwd: str, *, env: Mapping[str, str] | None = None, now: int | None = None) -> str`.
- `resolve_implement_tmpdir_main(argv: list[str]) -> int`.

Preserve these rules:

- Empty `hook_cwd` returns `""` and exits 0.
- Candidate dirs are `claude-implement-*` under the three roots.
- Accept the first existing sentinel in this order:
  1. `design-export/manifest.env`
  2. `review-round-summary.md`
  3. `.bump-version-armed`
  4. `.release-armed`
- Require `.larch-keepalive`.
- Parse `CLONE_PATH=` and `SESSION_ID=` as raw `key=value` lines; preserve everything after the first `=`.
- Require exact `CLONE_PATH == hook_cwd`.
- When `LARCH_TOKEN_SESSION_ID` is set, require exact `SESSION_ID` match.
- When session-id binding is not active, apply `LARCH_IMPLEMENT_TMPDIR_TTL_SECONDS`.
  - Default: `21600`.
  - Non-numeric: `21600`.
  - `0`: disable TTL.
  - Reject when `now <= 0`.
  - Reject when `(now - sentinel_mtime) >= ttl` (age exactly equal to TTL is stale).
- Exact session-id matches bypass TTL.
- Select newest accepted sentinel mtime.
- On equal mtime, choose the lexicographically smaller directory path.
- Skip unreadable or malformed candidates.
- Return only the selected path string or `""`.

CLI contract:

- Add `session resolve-implement-tmpdir --cwd <cwd>`.
- Default missing `--cwd` to `""` so hook usage remains fail-open.
- Emit the path to stdout when non-empty.
- Emit nothing when empty.
- Return 0 for normal no-match.
- Return 1 only for parser/runtime errors.

### UPDATED: python/cli.py

- Register `("session", "resolve-implement-tmpdir")`.
- Add it to `_MACHINE_STDOUT_KEYS` so inherited quiet mode cannot hide stdout.

### UPDATED: python/test_session_env.py

Replace the deleted bash harness coverage with Python tests.

Cover:

- Empty cwd returns empty output.
- `CLONE_PATH` routes concurrent worktrees correctly.
- `CLONE_PATH` value containing `=` is matched using everything after the first `=`.
- `LARCH_TOKEN_SESSION_ID` disambiguates same-`CLONE_PATH` candidates.
- Non-matching `SESSION_ID` disqualifies a candidate.
- `.bump-version-armed` and `.release-armed` remain eligible.
- Sentinel acceptance order uses the first existing sentinel per candidate.
- TTL rejects stale candidates when no session id is bound.
- Age exactly equal to `LARCH_IMPLEMENT_TMPDIR_TTL_SECONDS` is rejected.
- TTL `0` disables age rejection.
- Exact session-id match bypasses TTL.
- Newest mtime wins.
- Equal mtime uses lexicographically smaller directory path.
- CLI prints the resolved path and prints nothing for no match.

### UPDATED: skills/implement/scripts/hook-stop-fail-close.sh

Repoint resolver use.

- Remove `source "$SCRIPT_DIR/lib-resolve-implement-tmpdir.sh"`.
- Keep existing JSON parsing and `LARCH_TOKEN_SESSION_ID` export.
- Add a tiny bash-side pre-check before spawning Python:
  - Return false when `HOOK_CWD` is empty.
  - Scan these roots in order for at least one `claude-implement-*` directory:
    1. `${XDG_CACHE_HOME:-${HOME:-/tmp}/.cache}/larch/sessions`
    2. `/tmp`
    3. `/private/tmp`
  - Use bash glob + `[[ -d "$dir" ]]`; do not run Python when none exists.
- If the pre-check passes and `python3` exists, capture fail-open:

  `IMPLEMENT_TMPDIR=$(python3 "$PLUGIN_ROOT/python/cli.py" session resolve-implement-tmpdir --cwd "$HOOK_CWD" 2>/dev/null) || IMPLEMENT_TMPDIR=""`

- Preserve fail-open:
  - Missing `python3` resolves empty.
  - Non-zero CLI exit resolves empty.
  - Empty stdout exits 0.
- Keep the existing `.run-cleaned-up` and post-/review blocking logic unchanged.

### UPDATED: scripts/sessionstart-health.sh

Repoint resolver use.

- Remove dynamic sourcing of `skills/implement/scripts/lib-resolve-implement-tmpdir.sh`.
- Keep `jq` payload parsing for `cwd` and `session_id`.
- Keep exporting or unsetting `LARCH_TOKEN_SESSION_ID` before the resolver call.
- Add the same cheap bash-side `claude-implement-*` pre-check using the identical three-root list:
  - `${XDG_CACHE_HOME:-${HOME:-/tmp}/.cache}/larch/sessions`
  - `/tmp`
  - `/private/tmp`
- Only spawn Python when:
  - `HOOK_CWD` is non-empty,
  - the pre-check finds at least one session dir,
  - `python3` exists.
- Capture resolver stdout fail-open under `set -euo pipefail`:

  `IMPLEMENT_TMPDIR=$(python3 "$PLUGIN_ROOT/python/cli.py" session resolve-implement-tmpdir --cwd "$HOOK_CWD" 2>/dev/null) || IMPLEMENT_TMPDIR=""`

  Do not rely on prose-only "non-zero resolves empty"; the `|| IMPLEMENT_TMPDIR=""` guard is required.
- Empty stdout means no boundary advisory.
- Keep all existing advisory content and exit-0 behavior.

### UPDATED: scripts/test-sessionstart-health.sh

- Add `python3` to the controlled `real_bin` for cases that expect boundary resolution.
- Add a **structural** no-spawn assertion (do **not** use a marker-based runtime case):
  - Grep `scripts/sessionstart-health.sh` and assert the `claude-implement-*` pre-check appears on an earlier line than the `session resolve-implement-tmpdir` Python invocation (same ordered-source pattern as `scripts/test-design-structure.sh`).
  - Assert the pre-check guards the Python spawn path (e.g. pre-check failure branch returns or skips before `python3`).
  - Do **not** install a `python3` marker stub and assert it stays absent while assuming no global `claude-implement-*` dirs exist under `/tmp` or `/private/tmp`; unrelated stale dirs there would invoke the stub and flake `make lint`.
- Add a pre-check-pass / resolver-fail **runtime** regression case:
  - Create a dummy `claude-implement-*` dir under the harness-controlled cache root so the pre-check passes.
  - Install a `python3` stub that exits non-zero.
  - Assert exit code 0, stdout empty or advisory-only without boundary text, and SessionStart does not abort under `set -e`.
- Add or extend an `XDG_CACHE_HOME`-only case (no `HOME` override) proving resolution and pre-check scan the cache root `${XDG_CACHE_HOME}/larch/sessions`.
- Keep the existing `.run-cleaned-up`, post-/review, and retired release-advisory cases.

### UPDATED: scripts/test-implement-anti-halt.sh

Update structural checks for the Stop hook.

- Keep the `review-round-summary.md` sentinel check.
- Add checks that the hook now calls `session resolve-implement-tmpdir`.
- Add checks that the hook contains the `claude-implement-*` pre-check before the Python call (ordered-source / line-number assertion).
- Add a structural check that resolver capture uses `|| IMPLEMENT_TMPDIR=""` (or equivalent fail-open wrapper).

### UPDATED: skills/implement/scripts/hook-stop-fail-close.md

Update the contract.

- Replace the bash-lib sync note with the Python resolver CLI.
- Document the bash pre-check with the exact three-root formula.
- Document fail-open capture: `IMPLEMENT_TMPDIR=$(python3 ... 2>/dev/null) || IMPLEMENT_TMPDIR=""`.
- Preserve the fail-open Stop hook contract.

### UPDATED: scripts/sessionstart-health.md

Update the contract.

- Replace the bash-lib reference with `python/cli.py session resolve-implement-tmpdir`.
- Document the cheap pre-check, the exact three-root formula, and fail-open behavior.
- Require the explicit capture pattern:

  `IMPLEMENT_TMPDIR=$(python3 "$PLUGIN_ROOT/python/cli.py" session resolve-implement-tmpdir --cwd "$HOOK_CWD" 2>/dev/null) || IMPLEMENT_TMPDIR=""`

  and note that bare command substitution without `|| IMPLEMENT_TMPDIR=""` breaks the always-exit-0 contract under `set -e`.
- Keep the advisory-only semantics unchanged.

### UPDATED: SECURITY.md

Update the SessionStart tmpdir advisory section.

- Replace the deleted bash lib reference with the Python CLI resolver.
- Document that bash first checks for `claude-implement-*` dirs under `${XDG_CACHE_HOME:-${HOME:-/tmp}/.cache}/larch/sessions`, `/tmp`, and `/private/tmp` to avoid steady-state Python spawns.
- Keep the trust boundary:
  - local-only reads,
  - `.larch-keepalive` exact binding,
  - `SESSION_ID` binding,
  - TTL fallback,
  - basename-only disclosure.
- Include `.bump-version-armed` and `.release-armed` as legacy sentinel compatibility.

### UPDATED: docs/linting.md

Update lint docs.

- Remove the stale `make test-resolve-implement-tmpdir` row.
- Note that resolver regression coverage now lives in `python/test_session_env.py`.
- Keep the `make lint-retired-scripts`, `make lint`, `make py-lint`, and `make py-test` guidance intact.

### UPDATED: Makefile

Remove stale harness registration.

- Remove `test-resolve-implement-tmpdir` from `.PHONY`.
- Remove any target body if present.
- Do not add a replacement make target; Python coverage runs through `make py-test`.

### UPDATED: agent-lint.toml

Remove dead-script allowlist entries for deleted files.

- Remove `skills/implement/scripts/lib-resolve-implement-tmpdir.sh`.
- Remove `skills/implement/scripts/lib-resolve-implement-tmpdir.md`.
- Remove `skills/implement/scripts/test-resolve-implement-tmpdir.sh`.
- Remove `skills/implement/scripts/test-resolve-implement-tmpdir.md`.
- Remove or rewrite the Makefile-only comment block at lines 1123-1124 that still cites `test-resolve-implement-tmpdir` (otherwise `make lint-retired-scripts` fails after those paths land in `python/migrated-scripts.tsv`).
- Keep `hook-stop-fail-close.sh` and `.md` allowlist entries if still needed by hook registration.

### UPDATED: python/migrated-scripts.tsv

Append retired paths with the current issue id:

- `skills/implement/scripts/lib-resolve-implement-tmpdir.sh	#4515`
- `skills/implement/scripts/lib-resolve-implement-tmpdir.md	#4515`
- `skills/implement/scripts/test-resolve-implement-tmpdir.sh	#4515`
- `skills/implement/scripts/test-resolve-implement-tmpdir.md	#4515`

### UPDATED: skills/implement/scripts/lib-resolve-implement-tmpdir.sh

Delete this file after the Python resolver and hook repoints land.

### UPDATED: skills/implement/scripts/lib-resolve-implement-tmpdir.md

Delete this contract sibling after docs move to the Python resolver and hook docs.

### UPDATED: skills/implement/scripts/test-resolve-implement-tmpdir.sh

Delete this harness after equivalent coverage lands in `python/test_session_env.py`.

### UPDATED: skills/implement/scripts/test-resolve-implement-tmpdir.md

Delete this harness contract sibling.

## Edge cases

- **No cwd in hook payload**: resolver returns empty. Hooks exit 0.
- **No session dirs**: bash pre-check skips Python; pin with structural ordering assertions, not a marker-stub runtime case that assumes empty `/tmp` and `/private/tmp`.
- **Session dirs exist but Python fails**: SessionStart must still exit 0 via `|| IMPLEMENT_TMPDIR=""`.
- **Missing `python3`**: hooks resolve empty and continue.
- **Malformed keepalive**: candidate is skipped.
- **Multiple `=` in keepalive value**: preserve everything after the first `=`.
- **Session id set but absent in keepalive**: candidate is skipped.
- **TTL env malformed**: use `21600`.
- **TTL boundary**: age exactly equal to TTL is stale (`>=`).
- **Equal mtimes**: choose lexicographically smaller dir path.
- **Long-running exact-session run**: session-id match bypasses TTL.
- **`XDG_CACHE_HOME` without `HOME`**: pre-check and resolver both scan `${XDG_CACHE_HOME}/larch/sessions`.

## Failure modes

- **Python CLI import failure in a hook**: fail open with no tmpdir.
- **Resolver stdout polluted by quiet mode**: prevent by adding the CLI key to `_MACHINE_STDOUT_KEYS`.
- **SessionStart bare command substitution under `set -e`**: aborts hook before `exit 0`; prevent with explicit `|| IMPLEMENT_TMPDIR=""`.
- **Pre-check root formula drift**: boundary advisories silently fail open; prevent by pinning the same three-root literal in both hooks and testing `XDG_CACHE_HOME`-only resolution.
- **No-spawn regression untested or flaky**: marker-based runtime stubs false-fail when unrelated `claude-implement-*` dirs exist under global `/tmp` or `/private/tmp`; prevent with structural pre-check ordering assertions in `test-sessionstart-health.sh` and `test-implement-anti-halt.sh`, plus the harness-controlled pre-check-pass / resolver-fail runtime case for fail-open under `set -e`.
- **Deleted paths still referenced**: `make lint-retired-scripts` should catch this, including stale `agent-lint.toml` comment allowlist rows.
- **Controlled PATH tests miss `python3`**: update SessionStart harness bins explicitly.

## Testing strategy

Run focused tests first:

- `python3 -m pytest python/test_session_env.py -q -k 'resolve_implement_tmpdir or setup_writes_session_id'`
- `python3 -m pytest python/test_cli.py -q -k 'registry or machine_stdout'`
- `bash scripts/test-sessionstart-health.sh`
- `bash scripts/test-implement-anti-halt.sh`

Then run required checks:

- `make lint-retired-scripts`
- `make lint`
- `make py-lint`
- `make py-test`

## Acceptance

- `resolve_implement_tmpdir` logic is ported to `python/session_env.py` (stdlib-only) and reachable as `python3 python/cli.py session resolve-implement-tmpdir --cwd <cwd>`, which prints the resolved path on stdout (nothing when none) and preserves the bash resolver's algorithm exactly: the three roots, sentinel acceptance order, `.larch-keepalive` `CLONE_PATH`/`SESSION_ID` binding, TTL backstop, newest-mtime with lexicographic tie-break, and fail-open on empty cwd.
- `skills/implement/scripts/hook-stop-fail-close.sh` and `scripts/sessionstart-health.sh` no longer source the bash lib. Each runs a cheap bash pre-check over the three roots and only spawns `python3` when a `claude-implement-*` dir exists. Both stay fail-open: a non-zero CLI exit or empty stdout resolves to empty and the hook exits 0. SessionStart uses the explicit `|| IMPLEMENT_TMPDIR=""` capture so `set -e` cannot abort it.
- `lib-resolve-implement-tmpdir.sh`, its `.md`, `test-resolve-implement-tmpdir.sh`, and its `.md` are deleted and appended to `python/migrated-scripts.tsv` tagged `#4515`. Stale references in `Makefile`, `agent-lint.toml` (allowlist entries plus the lines 1123-1124 comment), and `docs/linting.md` are removed.
- `SECURITY.md` and `docs/linting.md` describe the Python resolver CLI and the bash pre-check instead of the deleted lib.
- `python/test_session_env.py` covers the resolver (empty cwd, `CLONE_PATH` routing, `=`-in-value, session-id disambiguation, sentinel order, TTL boundary and disable, mtime tie-break, CLI output); `test-sessionstart-health.sh` and `test-implement-anti-halt.sh` cover the repointed hooks structurally plus a pre-check-pass / resolver-fail fail-open case.
- `make lint-retired-scripts`, `make lint`, `make py-lint`, and `make py-test` are all green.
- The two hooks remain bash; no hook overhaul, daemon, or `progress_report.py` consolidation is introduced.

review_status: complete
rounds_completed: 3
diff_lines: 580
