## Proposed Design Outline

### Goals
- Make `larch/io.py` the single read owner: migrate ~20 `split("=", 1)` loops to `parse_kv`/`kv_value`
- Unify `_emit_kv` private wrappers: delete all 10+ copies, call `logging_util.emit_kv` directly
- Add `cli.py kv get` Bash funnel and adoption-ratchet lint blocking new ad-hoc parsers

### Non-goals
- Changing `env_file.py`'s shell-quoting (`export KEY='v'`) path (different grammar, distinct callers)
- Changing `parse_allowlisted_env_line` in `session_env.py` (validates allowlists, not just parsing)
- Changing the existing `read-result-env` CLI verb (already handles Bash side for design steps)

### Approach sketch
- Audit each `split("=", 1)` site; replace with `kv_value()` or `parse_kv()` with explicit policy flag
- Delete private `_emit_kv` wrappers from `git/`, `implement/`, `state/`, `issue/`, `agents/`; call `logging_util.emit_kv` directly
- Add `("kv", "get")` CLI sub-command backed by `larch_io.kv_value()` for Bash callers
- Add `lint_kv_codec.py` + baseline JSON via the #6992 lint-engine pattern; register in `cli.py` and `Makefile`

### Surfaces in scope
- `python/larch/io.py` (verify/extend policy params if needed)
- `python/larch/design/` — `design_core.py`, `design_publish.py`, `design_pause.py`, `design_summary.py`, `design_oos.py`, `design_terminal.py`, `clarify.py`, `design_router.py`
- `python/larch/state/` — `ship_state.py`, `session_env.py`
- `python/larch/implement/` — `ci.py`, `preflight.py`
- `python/larch/run_context.py`, `python/larch/agents/_types.py`, `python/larch/issue/deps_audit.py`
- `python/larch/git/` — `push.py`, `pr.py`, `pr_body.py`, `merge.py`, `git.py`
- `python/cli.py` (add `kv get` sub-command)
- `python/larch/lint/lint_kv_codec.py` + `python/lint-kv-codec-baseline.json` (new files)
- `python/tests/lint/test_lint_kv_codec.py` (new tests)
- `Makefile` (lint target + CI wiring)

### Open questions
- None.
