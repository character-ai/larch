## Decision 1: Fix scope
- **Question**: What scope should the fix for the stale `LARCH_TOKEN_SESSION_ID` Stop-hook bug cover?
- **Resolution**: Add the missing `else unset LARCH_TOKEN_SESSION_ID || true` branch to the Stop hook (mirror the SessionStart hook's exact pattern) and update the `.md` sibling contract. Add NO new regression test; rely on the existing static `scripts/test-implement-anti-halt.sh` harness.
- **Source**: user

## Decision 2: SessionStart hook is out of scope
- **Question**: Does the parallel SessionStart hook (`scripts/sessionstart-health.sh`) need the same fix?
- **Resolution**: No. It already exports-or-unsets correctly (the `if [[ -n "$SID" ]]; then export ...; else unset LARCH_TOKEN_SESSION_ID || true; fi` block). It is the reference pattern to mirror, not a fix target. No other conditional-export site is stale-payload-derived (the `/implement` step scripts rehydrate from a session-env file).
- **Source**: codebase

## Decision 3: Hard constraints to preserve
- **Question**: What existing behavior must not break?
- **Resolution**: (a) Hook must remain fail-open and always `exit 0` (`set -uo pipefail`; `-e` intentionally omitted per `.claude/rules/shell-strict-mode.md`). (b) `unset` must tolerate `set -u` via `|| true`. (c) Must not break the existing static assertions in `scripts/test-implement-anti-halt.sh` (they check the `resolve-implement-tmpdir` capture shape, not the SID export line). (d) Keep the SID handling at its current location (before the resolver block), since `LARCH_TOKEN_SESSION_ID` only feeds the `resolve-implement-tmpdir` child.
- **Source**: codebase
