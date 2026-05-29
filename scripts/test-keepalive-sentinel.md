# scripts/test-keepalive-sentinel.sh — contract

Regression harness for `scripts/session-setup.sh` session identity metadata. It runs `session-setup.sh` with preflight and repo discovery disabled inside a temporary `XDG_CACHE_HOME`, then asserts:

- the session tmpdir is created under `${XDG_CACHE_HOME}/larch/sessions/`;
- `SESSION_ID=` is emitted and matches `session-id`;
- `LARCH_RENDER_CACHE_DIR=` points at `SESSION_TMPDIR/render-cache`;
- `.larch-keepalive` exists with the slim identity header, `CLONE_PATH=`, and `SESSION_ID=` only (no legacy `PID`, `PPID`, `PREFIX`, `CREATED`, or `NOTE` fields).

Primary contract owner: `scripts/session-setup.md`.
