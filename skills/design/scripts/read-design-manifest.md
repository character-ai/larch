`skills/design/scripts/read-design-manifest.sh` safely parses and verifies `$IMPLEMENT_TMPDIR/design-export/manifest.env` for `/implement` Step 1. It emits `MANIFEST_OK=true` plus verified path keys on success, or `MANIFEST_FAILED=true ERROR=<token>` on failure. It never exits non-zero for manifest rejection; the caller branches on stdout.

Security invariants:
- Parse `KEY=VALUE` line by line; never `source` or `eval`.
- Reject malformed keys, malformed lines, unsupported versions, control characters in values, non-absolute paths, symlinks, non-regular files, and paths that resolve outside `$IMPLEMENT_TMPDIR/design-export/`.
- Enforce non-empty policy for `PLAN_FILE` and `PLAN_REVIEW_TALLY_FILE`.

Edit in sync with `write-design-manifest.sh`, `test-design-manifest.sh`, `/design` Step 5, and `/implement` Step 1 whenever the manifest schema or failure tokens change.
