### OOS_1: [OUT_OF_SCOPE] No harness coverage for scoped TMPDIR `marker_candidates()` discovery
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: Existing hook harnesses stub discovery via `LARCH_BG_POLL_GUARD_MARKER` and do not exercise the new scoped `$TMPDIR` branch without that override. A regression in prefix scoping (e.g. dropping `claude-implement-*`) would not be caught by CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Add offline tests placing markers under scoped TMPDIR dirs and asserting discovery behavior.

### OOS_2: [OUT_OF_SCOPE] Cache branch hardcodes `$HOME/.cache/larch/sessions` despite `XDG_CACHE_HOME`
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: `marker_candidates()` hardcodes `$HOME/.cache/larch/sessions`, while session setup honors `XDG_CACHE_HOME` via `cleanup_cache_sessions_root()`. Users with a non-default `XDG_CACHE_HOME` may not be scanned by the cache branch. Pre-existing; not introduced by this diff.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_3: [OUT_OF_SCOPE] Nested `$TMPDIR` layouts accepted by allowlist but omitted from scoped scan
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-shell-compat
- **Severity**: latent
- **Concern**: `is_allowed_marker_parent()` still accepts nested `$TMPDIR/*/larch-*` and `$TMPDIR/*/claude-design-*`, but the new TMPDIR scan only inspects direct `$TMPDIR/larch-*` and `$TMPDIR/claude-design-*` children. The old broad `find … -maxdepth 3` could discover nested markers. No production session-setup path in this repo creates nested design/implement tmpdirs under `$TMPDIR`; low materiality today.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Either add a nested-prefix scan or drop the nested patterns from `is_allowed_marker_parent()` for consistency.

### OOS_4: [OUT_OF_SCOPE] Hook harnesses do not exercise auto-discovery through scoped `$TMPDIR`
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing, dyn-dyn-shell-compat
- **Severity**: nit
- **Concern**: Hook harnesses always set `LARCH_BG_POLL_GUARD_MARKER` or use `~/.cache/larch/sessions` fixtures, so automatic `marker_candidates()` TMPDIR discovery (including the new scoped glob) is not regression-tested. A typo in the new glob or depth limit would only show up in production.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add one discovery-only test per harness.
  - From codex-specialist-testing: Add one offline fixture that creates a real .bg-wait-active under a matching TMPDIR-prefixed directory and verifies both hooks still discover it; cover the mirrored logic in scripts/hook-no-progress-guard.sh:62-76 with the same case.

### OOS_5: [OUT_OF_SCOPE] `hooks.json` timeout raise not asserted in hook harness
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: The harness asserts `hooks.json` registration for `hook-bg-poll-guard.sh` but not `timeout == 10`, unlike `test-hook-progress-report.sh` and `test-sweep-design-logs.sh`. Half of Option C (the timeout raise) could revert without CI catching it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add jq assertions for `timeout == 10` on all three changed hook registrations.

### OOS_6: [OUT_OF_SCOPE] Pre-existing asymmetry: `marker_is_live` enforces parent allowlist, `is_marker_live` does not
- **Reviewer(s)**: dyn-dyn-shell-compat
- **Severity**: latent
- **Concern**: Pre-existing asymmetry between `hook-bg-poll-guard.sh` and `hook-no-progress-guard.sh`: `marker_is_live` enforces `is_allowed_marker_parent`; `is_marker_live` does not. That is why the missing `claude-implement-*` glob changes behavior for the no-progress guard on the TMPDIR fallback path but not for the bg-poll guard (which already rejected `$TMPDIR/claude-implement-*` parents).
- **Suggested revisions (informational for voters; coder decides)**:

