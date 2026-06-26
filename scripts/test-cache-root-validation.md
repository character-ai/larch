# scripts/test-cache-root-validation.sh — contract

Regression harness for the three larch session tmpdir validators widened for cache-backed session roots:

- `python/cli.py session cleanup-tmpdir` accepts `${XDG_CACHE_HOME}/larch/sessions/...`;
- `python3 python/cli.py implement-finalize teardown` accepts state and tmpdir paths under that same root;
- `python3 python/cli.py token lane-write/lane-report` accepts the same root through `validate_dir`;
- legacy `/tmp/` and, when present, `/private/tmp/` remain accepted;
- unrelated paths remain rejected.

Primary contract owners: `python/larch/state/session_env.py (session cleanup-tmpdir)`, `python/larch/state/finalize.py`, and `python/tokens.py research lane docs`.
