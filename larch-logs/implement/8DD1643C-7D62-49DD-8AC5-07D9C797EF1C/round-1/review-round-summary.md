# Review Round 1

- Mode: `diff`
- 1 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Scoped TMPDIR glob omits `claude-implement-*` on cache-fallback paths
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, codex-generalist, dyn-dyn-shell-compat
- **Severity**: important
- **Concern**: Both hooks' `marker_candidates()` TMPDIR loops only glob `larch-*` and `claude-design-*`, but `/implement` session setup can create `claude-implement-{clone}-*` tmpdirs under `${TMPDIR:-/tmp}` when the cache session root is unavailable (`python/larch/state/session_env.py`). The prior broad `${TMPDIR:-/tmp}` `find` discovered `/tmp/claude-implement-*/.bg-wait-active`; the scoped loop does not. On that fallback path, `hook-no-progress-guard.sh` no longer arms the circuit breaker for live implement bg-waits. `hook-bg-poll-guard.sh` shares the same scoped omission and its `is_allowed_marker_parent()` also omits direct `$tmp_root/claude-implement-*`, so poll-guard discovery and allowlisting are both blind to implement fallback tmpdirs outside `*/.cache/larch/sessions/*`. Normal cache-backed runs under `~/.cache/larch/sessions/` remain covered by the unchanged cache branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Add "${TMPDIR:-/tmp}"/claude-implement-* to the prefix loop in both hooks' marker_candidates().
  - From codex-specialist-correctness: add claude-implement-* to the TMPDIR scan or derive prefixes from session setup, and add a regression test for the fallback path
  - From codex-specialist-edge-cases: Add claude-implement-* to the scoped search, or centralize the allowed tmpdir-prefix list in the session resolver and reuse it here.
  - From codex-generalist: Include `claude-implement-*` in the scoped TMPDIR candidate set, and update `hook-bg-poll-guard.sh`'s `is_allowed_marker_parent` plus both docs to keep implement fallback tmpdirs covered without restoring the broad TMPDIR scan.
  - From dyn-dyn-shell-compat: Add `"${TMPDIR:-/tmp}"/claude-implement-*` to the `for` glob list in both hooks' `marker_candidates()` (and extend `is_allowed_marker_parent` in `hook-bg-poll-guard.sh` to accept `"$tmp_root"/claude-implement-*` for parity), or document and test that implement markers are intentionally cache-only.


