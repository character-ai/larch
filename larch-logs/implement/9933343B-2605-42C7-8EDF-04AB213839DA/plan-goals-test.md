## Goal
Extend cursor-ci stall handler with richer diagnostic artifacts (lsof, full ps tree, git state, transcript tail) written as a JSON sidecar, add audit-scan for stall-cause distribution, and add regression test.

## Implementation Plan
## Plan

### Files / globs to touch

1. `scripts/launch-cursor-ci.sh` — stall handler call site
   (search anchor: `Stall detected` literal). Add stack/state capture
   on stall + emit a richer sidecar artifact.
2. `scripts/launch-cursor-ci.md` — document the new sidecar artifact
   and its location.
3. `scripts/test-launch-cursor-ci.sh` — regression case asserting
   the new artifact is emitted on synthetic stall.
4. `.claude/skills/audit-runs/scans.tsv` and
   `.claude/skills/audit-runs/scripts/audit-scan-run.sh` — extend
   the existing stall-tracking surface with a new
   `cursor-ci-stall-causes` scan that aggregates causes across run
   logs (so post-mitigation audits can measure reduction).
5. `scripts/ship-pr.sh` — stall-aware retry policy (Phase 2 only;
   gate on Phase 1 diagnostic data).

### Sequenced steps

#### Phase 1 — Diagnostic capture (low-risk; ship first)

1. **Identify the stall handler in `scripts/launch-cursor-ci.sh`.**
   The stall handler runs when `time_since_last_progress` crosses the
   180s threshold (search anchor: `Stall detected` literal). Today it
   captures `ps` snapshots for the target pid and direct children;
   extend it to capture:
   - `lsof -p <pid>` (file descriptors held; helps spot hung file/socket
     I/O).
   - `ps -ef | grep cursor` (full process tree; helps spot daemon
     processes or stuck child workers).
   - `git status` + `git rebase --show-current-patch` (when running in
     a rebase context — the `Step CI resolve-conflict` site).
   - The cursor process's most-recent transcript line (last 50 lines
     of stdout/stderr captured before the stall, if available).

   Write each artifact to a per-stall sidecar under the run-log
   directory: `round-N/cursor-ci-stall-<timestamp>.json` (JSON-shaped:
   `{channel, pid, time_since_last_progress, ps, lsof, git_state,
   last_transcript_lines}`). Reuse the existing
   `aggregator-validate.stderr`-style sidecar convention.

2. **Document the new artifact** in `scripts/launch-cursor-ci.md`.

3. **Regression test**.
   In `scripts/test-launch-cursor-ci.sh`, add a synthetic-stall case
   (force a long sleep on the target pid). Assert
   `round-1/cursor-ci-stall-*.json` is emitted with a non-empty
   `ps` field and (when feasible in the harness) `lsof`/`git_state`
   fields. Keep the existing stall-detection test cases PASS.

4. **Audit-side scan registry**.
   Add a row to `.claude/skills/audit-runs/scans.tsv` for
   `cursor-ci-stall-causes` (type `glob`, pattern
   `round-*/cursor-ci-stall-*.json`, expected_outcome `informational`).
   Wire a matching scan function in `audit-scan-run.sh` that
   aggregates `channel` values (`stdout` / `tree:<path>` / etc.) so
   future audits can summarize stall-cause distribution. Update
   `audit-scan-run.md` to list the new scan.

5. **`/relevant-checks` + run the new harness**.

#### Phase 2 — Mitigation (after Phase 1 data is in)

6. **Stall-aware retry policy in `scripts/ship-pr.sh`.**
   After Phase 1 lands and ≥2 audit runs have captured cursor-ci-stall
   sidecars, analyze them: when stalls cluster on a single channel
   (e.g., `stdout`), consider:
   - Reducing the stall threshold from 180s to a shorter value for
     known-fast steps (e.g., 90s for `Step CI fix` after Phase 1 data
     shows real progress lines are emitted within seconds for that
     step).
   - Adding a kill-and-retry-with-backoff before exhausting cursor-ci
     `retries=1` — the existing single retry is consumed by the next
     stall instead of giving the underlying cause time to clear.
   - Detecting and skipping demonstrably-stuck patterns (e.g., a
     keychain-lock signature in `lsof` output → emit a clear error
     instead of stalling).

   The specific mitigation depends on Phase 1 data. Track each
   mitigation choice in a follow-up PR; keep this issue's acceptance
   focused on the diagnostic-capture surface.

### Breaking changes

None. Phase 1 is purely additive (richer stall artifacts; new scan
row). The Phase 2 retry policy will be gated behind explicit operator
opt-in or behind a flag if the change risks regressing
short-stall edge cases.

### Closed decisions

- **Diagnostic-first**: do not adjust stall thresholds or retry
  counts until Phase 1 data quantifies the cause distribution. The
  prior #2515 fix landed detection without root-cause investigation;
  this issue inverts that order.
- **JSON sidecar over flat text**: the structured shape lets the
  audit-scan aggregate `channel` and `cause-signature` counts without
  fragile grep heuristics.
- **Audit-side scan in `audit-scan-run.sh`** so the issue's
  effectiveness is measurable across runs.

## Acceptance (Phase 1 — shippable)

1. `bash scripts/test-launch-cursor-ci.sh` exits 0 with the new
   synthetic-stall sidecar case PASS.
2. A staged stall (force `sleep 200` on a worker) writes
   `round-1/cursor-ci-stall-<timestamp>.json` with non-empty `ps`
   and `channel` fields.
3. `bash .claude/skills/audit-runs/scripts/test-audit-runs.sh` PASSes
   with the new `cursor-ci-stall-causes` scan exercised.
4. `/relevant-checks` passes with no new warnings introduced under
   `scripts/` or `.claude/skills/audit-runs/`.
5. After landing, the next `/audit-runs since last audit` run with at
   least one cursor-ci stall emits an `informational` row from
   `cursor-ci-stall-causes` showing the channel distribution.

## Acceptance (Phase 2 — gated on Phase 1 data)

6. (Future PR) Stall-aware retry policy reduces cursor-ci stall
   occurrences by ≥50% across two consecutive audit batches.
   Specific mitigation tactics to be decided after Phase 1 data is
   in; this acceptance row is a tracking placeholder.

## Test plan
(no test plan section in plan-file)
