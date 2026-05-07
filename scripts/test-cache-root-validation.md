# scripts/test-cache-root-validation.sh — contract

Regression harness for the three larch session tmpdir validators widened for cache-backed session roots:

- `scripts/cleanup-tmpdir.sh` accepts `${XDG_CACHE_HOME}/larch/sessions/...`;
- `scripts/implement-finalize.sh teardown` accepts state and tmpdir paths under that same root;
- `scripts/token-tally.sh` accepts the same root through `validate_dir`;
- legacy `/tmp/` and, when present, `/private/tmp/` remain accepted;
- unrelated paths remain rejected.

Primary contract owners: `scripts/cleanup-tmpdir.md`, `scripts/implement-finalize.md`, and `scripts/token-tally.md`.
