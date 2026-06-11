## Goal
Implement issue #4038: [IMPLEMENTING] [BUG] /implement final report missing "Review Phase Detail" table: `render-review-phase-detail.sh` requires `round-meta.json` which the code review pipeline never writes\n\n**Symptom.**.

## Implementation Plan
**Symptom.**

The `/implement` final report (Step 17 `summary-final.md`) always shows only:

```
- **Code review**: N/M accepted
```

The "Review Phase Detail" table (per-round row with suggestions made/accepted, OOS counts, duration, cost, reviewers launched) is never emitted, even for panel code review runs with multiple rounds and accepted findings.

**Root cause.**

`write-final-report.sh` calls `render-review-phase-detail.sh --rounds-root "$IMPLEMENT_TMPDIR/larch-logs/implement/$RUN_ID"` to generate the table. That script iterates over `round-N/` directories and at line 80 gates each round on the presence of `round-meta.json`:

```bash
[ -f "$d/round-meta.json" ] || continue
```

If no round has a `round-meta.json`, the script calls `finalize_empty` (produces empty output) and exits 0. The review detail section is silently dropped from the final report.

The `/implement` code review pipeline does **not** write `round-meta.json` to round directories. The committed run logs confirm this: `round-1/`, `round-2/`, `round-3/` each contain `code-voter-slots.ndjson`, `panel-manifest.ndjson`, `review-round-summary.md`, `findings-classification.tsv`, and others — but no `round-meta.json`.

`scripts/write-design-round-meta.sh` creates `round-meta.json` for `/design` plan-review rounds from sidecar data. `scripts/consolidate-round-sidecars.sh` creates it retroactively from OLD-format sidecar files (`review-tally.env`, `collector-results.env`, etc.) for historical runs. Neither is called during live `/implement` code review rounds, and the old-format sidecars are absent from new runs anyway.

**Affected path.** Any `/implement` run that uses the code review panel (i.e., all non-`--self-review` runs): the Review Phase Detail section is always empty.

**Suggested fix (two options).**

Option A — **live writer**: create a `scripts/write-implement-round-meta.sh` script (analogous to `write-design-round-meta.sh`) that synthesises `round-meta.json` from the available new-format round artifacts (`code-voter-slots.ndjson`, `panel-manifest.ndjson`, `findings-classification.tsv`, `review-round-summary.md`). Call this writer from the code review loop (e.g., inside `review-and-fix.sh` or at the end of each round in `review-core.sh`) immediately after the round completes, before `run-log commit`. This way `round-meta.json` is present in the tmpdir-based larch-logs when `write-final-report.sh` runs at Step 17.

Option B — **reader-side adaptation**: update `render-review-phase-detail.sh` to fall back to reading per-round counts directly from `code-voter-slots.ndjson` (for accepted/rejected counts and slot info) and `panel-manifest.ndjson` (for reviewer details) when `round-meta.json` is absent. This makes the script more robust to format evolution without requiring all round directories to have a synthesized meta file.

Option A is preferred for consistency with the design phase and to keep `render-review-phase-detail.sh` as a pure renderer with a stable input contract.

**Evidence.** Verified on run `0A906712-C543-4473-B9F4-41D96E8E6597` (PR #4029, issue #3997): `larch-logs/implement/0A906712.../round-1/`, `round-2/`, `round-3/` all committed without `round-meta.json`; `summary-final.md` shows only `- **Code review**: 19/30 accepted` with no review table.

## Test plan
(no test plan section in plan-file)
