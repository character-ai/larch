## Decision 1: How to handle the documented blocker
- **Question**: Issue #4515 says "do not run prematurely" until a future bash-hook overhaul lands, because porting would add a python3 spawn per Stop event. How should the design proceed?
- **Resolution**: Proceed now with a gated python3 call. Port `resolve_implement_tmpdir` to `python/session_env.py`; repoint both hooks to a fail-open `python3 python/cli.py` resolver, gated by a cheap bash pre-check so python3 only spawns when a `claude-implement-*` session dir exists. No steady-state per-Stop regression. This satisfies the issue's own escape clause ("the hooks can otherwise call a Python CLI surface").
- **Source**: user

## Decision 2: The gate must be bash-side
- **Question**: Where does the "only spawn python3 when needed" gate live?
- **Resolution**: Bash-side, in each hook (or a tiny shared bash pre-check). A Python-side fast path would still spawn python3, defeating the purpose. The bash pre-check globs the session roots for `claude-implement-*` dirs and skips the python3 call when none exist.
- **Source**: codebase (consequence of Decision 1)

## Decision 3: Preserve resolution behavior exactly
- **Question**: Must the Python port reproduce the bash resolver's algorithm?
- **Resolution**: Yes. Preserve: fail-open on empty `hook_cwd`; manifest acceptance order (design-export/manifest.env, then review-round-summary.md, then `.bump-version-armed`, then `.release-armed`); `.larch-keepalive` `CLONE_PATH` match; `LARCH_TOKEN_SESSION_ID` exact `SESSION_ID` binding when set; TTL backstop (`LARCH_IMPLEMENT_TMPDIR_TTL_SECONDS`, default 21600) when session-id is unset; newest-by-mtime selection with lexicographically-smaller-dir tie-break; the three session roots (`${XDG_CACHE_HOME:-$HOME/.cache}/larch/sessions`, `/tmp`, `/private/tmp`). This behavior is pinned by the existing test harness and referenced by SECURITY.md.
- **Source**: codebase / issue (hard constraint)

## Decision 4: Hooks stay bash; fail-open preserved
- **Question**: Do the two hooks remain bash, and must they stay fail-open?
- **Resolution**: Yes to both. Per repo policy hooks stay bash. The resolver call must be fail-open: any non-zero python3 exit or empty stdout resolves to empty tmpdir and the hook exits 0 without blocking. Precedent: `scripts/hook-progress-report.sh` (`... || exit 0`).
- **Source**: codebase / issue (hard constraint)

## Decision 5: Consolidation with progress_report.py is out of scope
- **Question**: Should the port unify with the overlapping tmpdir resolution in `python/progress_report.py`?
- **Resolution**: No. `progress_report.py` resolves via `current-implement-env-*.sh` pointer files plus a different keepalive read; the bash lib globs `claude-implement-*` dirs by mtime/TTL. Unifying them is a behavior-changing refactor outside this issue. Keep the ports separate (minimum change).
- **Source**: codebase (minimum-change principle)

## Decision 6: Scope boundary (binding)
- **Question**: What is the full in-scope deliverable set?
- **Resolution**: (1) Port logic to Python (stdlib-only); (2) repoint `skills/implement/scripts/hook-stop-fail-close.sh` and `scripts/sessionstart-health.sh`; (3) delete `lib-resolve-implement-tmpdir.sh` + its `.md` + `test-resolve-implement-tmpdir.sh` + its `.md`; (4) add the deleted paths to `python/migrated-scripts.tsv`; (5) add Python test coverage in `python/test_session_env.py`; (6) update `SECURITY.md` and `docs/linting.md` where they reference the bash lib. Out of scope: hook overhaul, daemon, consolidation with progress_report.py.
- **Source**: issue
