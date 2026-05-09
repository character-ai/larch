# scripts/test-keepalive-sentinel.sh — contract

Regression harness for `scripts/session-setup.sh` keepalive metadata. It runs `session-setup.sh` with preflight and repo discovery disabled inside a temporary `XDG_CACHE_HOME`, then asserts:

- the session tmpdir is created under `${XDG_CACHE_HOME}/larch/sessions/`;
- `SESSION_ID=` is emitted and matches `session-id`;
- `.larch-keepalive` exists and contains the documented header keys.

Primary contract owner: `scripts/session-setup.md`.
