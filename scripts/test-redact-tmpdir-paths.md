# scripts/test-redact-tmpdir-paths.sh — contract

Regression harness for `scripts/redact-tmpdir-paths.sh`. It feeds representative legacy `/tmp`, macOS `/private/tmp`, clone-tagged session names, and cache-backed session paths through the helper, then checks prose embedding, non-matching preservation, idempotence, and JSON parseability after redacting multiple cache-backed paths on one line.

Primary contract owner: `scripts/redact-tmpdir-paths.md`.
