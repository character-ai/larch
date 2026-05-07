# scripts/test-finalize-sanity-check.sh — contract

Regression harness for the `/implement` Step 18 cleanup target sanity check in `scripts/implement-finalize.sh`.

The harness copies the finalizer into a `/tmp` sandbox with a stub `cleanup-tmpdir.sh`, then covers:

- happy-path basename prefix plus matching `session-id` invokes cleanup;
- foreign basename refuses cleanup, emits the documented warning, and appends to `execution-issues.md`;
- missing `session-id` with an expected id refuses cleanup;
- legacy state missing `EXPECTED_SESSION_ID` falls back to basename-only validation and still invokes cleanup.

Primary contract owner: `scripts/implement-finalize.md`.
