### [Plan Review] FINDING_3

### FINDING_3: NO_ADMIN_FALLBACK missing from canonical initial key set / allowed-keys parity
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The plan adds `NO_ADMIN_FALLBACK` to `_ALLOWED_SHIP_STATE_KEYS` but does not require the initial canonical constant to match the `write-initial-state-keys` marker byte-for-byte in one ordered list. `ship.py` today omits `NO_ADMIN_FALLBACK` from `_ALLOWED_SHIP_STATE_KEYS` while the SKILL marker and `step-8-ship.sh` already read/pass it. If `seed-initial-state` writes `NO_ADMIN_FALLBACK` but the first `_write_ship_state` refresh still drops it until driver emission is wired, merge/admin routing can disagree between seeded state and argv.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: When defining the canonical initial key constant, include NO_ADMIN_FALLBACK with the same default as the marker, assert the full ordered key list (marker keys + OOS_PENDING=false) in python/test_ship.py, and add one test that _write_ship_state preserves NO_ADMIN_FALLBACK after the allowed-keys change


### [Plan Review] FINDING_5

### FINDING_5: Contradictory plan requirements on retired read-session-env-key.sh reference
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The plan requires and forbids the same retired helper reference. The new seeder docs are told to explicitly cite `scripts/read-session-env-key.sh`, while the structure test is told to forbid seeder/wrapper contracts from referencing `read-session-env-key.sh`. Implementing both makes the planned validation fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Narrow the forbid assertion to executable call sites, or remove the literal retired-helper path from the new docs. Keep the required behavior as "use python/cli.py session read-key."


