`skills/design/scripts/write-design-manifest.sh` exports `/design` artifacts from `$DESIGN_TMPDIR` into `$IMPLEMENT_TMPDIR/design-export/` and atomically writes `$IMPLEMENT_TMPDIR/design-export/manifest.env` for `/implement` Step 1. It is invoked only by `/design` Step 5 after Step 3.5 / 3b / 4 have finished and before `$DESIGN_TMPDIR` cleanup.

Contract:
- `PLAN_FILE` and `PLAN_REVIEW_TALLY_FILE` are required non-empty artifacts.
- `CONTESTED_CRITERIA_FILE`, `OOS_FILE`, `REJECTED_FINDINGS_FILE`, and `ACCEPTED_PLAN_FINDINGS_FILE` are required files that may be empty.
- `ARCHITECTURE_DIAGRAM_FILE` is optional and omitted when generation soft-failed.
- `run-params.json` is internal-only. It is consumed during the same `/design` run and is deliberately not copied into `design-export/manifest.env`.
- `CONTESTED_CRITERIA_FILE` is the load-bearing manifest key whose value points at the sketch-phase dialectic inputs file `contested-decisions.md`. The "criteria" / "decisions" naming asymmetry is intentional and stable for `MANIFEST_VERSION=1` — renaming would be a breaking `MANIFEST_VERSION=2` migration.
- The manifest is written via `mktemp` plus `mv`; partial manifests must never be visible as `manifest.env`.
- `SESSION_ID` is stripped of all C0 control characters and DEL (`\000-\037`, `\177`) before being written, mirroring the reader's `check_value` policy. If stripping leaves it empty, the writer aborts with exit 1. Defense-in-depth: avoids generating a manifest the reader would reject.

Edit in sync with `read-design-manifest.sh`, `test-design-manifest.sh`, `/design` Step 5, and `/implement` Step 1 whenever the KV schema or per-key policy changes.
