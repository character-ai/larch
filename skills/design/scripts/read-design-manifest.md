`skills/design/scripts/read-design-manifest.sh` safely parses and verifies `$IMPLEMENT_TMPDIR/design-export/manifest.env` for `/implement` Step 1. It emits `MANIFEST_OK=true` plus verified path keys on success, or `MANIFEST_FAILED=true ERROR=<token>` on failure. It never exits non-zero for manifest rejection; the caller branches on stdout.

Security invariants:
- Parse `KEY=VALUE` line by line; never `source` or `eval`.
- Reject malformed keys, malformed lines, unsupported versions, control characters in values, non-absolute paths, symlinks, non-regular files, and paths that resolve outside `$IMPLEMENT_TMPDIR/design-export/`.
- Reject duplicate occurrences of any load-bearing key (e.g., a second `PLAN_FILE=` line) with `ERROR=duplicate-key:<KEY>`. Without this guard, a later duplicate could silently overwrite an earlier validated value with a different path that the caller treats as already-validated.
- Enforce non-empty policy for `PLAN_FILE` and `PLAN_REVIEW_TALLY_FILE`.

Schema naming note: `CONTESTED_CRITERIA_FILE` is the load-bearing manifest key whose value points at `contested-decisions.md` (sketch-phase dialectic inputs). The "criteria" / "decisions" naming asymmetry is intentional and stable for `MANIFEST_VERSION=1` — a rename would be a breaking-change `MANIFEST_VERSION=2` migration coordinated across `write-design-manifest.sh`, `read-design-manifest.sh`, `test-design-manifest.sh`, and any caller. Flagged here so grep-driven debugging finds the binding without surprise.
- Buffer per-path success output and emit `MANIFEST_OK=true` only AFTER every `check_path` succeeds. A `fail` between an early `MANIFEST_OK=true` print and a later rejection would leave a fail-open envelope on stdout that a fail-closed consumer would still parse as valid (`/review` Round 1 FINDING_1).

Edit in sync with `write-design-manifest.sh`, `test-design-manifest.sh`, `/design` Step 5, and `/implement` Step 1 whenever the manifest schema or failure tokens change.
