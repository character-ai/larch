## Goal
Implement issue #3538: [IMPLEMENTING] Track PR-metrics feature (#3506 bundled in #3514): add plan/acceptance criteria and fix fallback-renderer test gap\n\n## Out-of-Scope Observation.

## Implementation Plan
## Plan

# Plan: PR-metrics feature — retroactive plan/acceptance + fallback-renderer test gap

## Context

The PR-metrics feature shipped inside the #3514 PR without its own plan (surfaced as OOS, filed as #3538). It is live on main: `scripts/compute-pr-line-counts.sh` computes bucketed PR diff line counts, `scripts/render-run-summary.sh` renders the `Lines (PR diff)` bullet, and `skills/implement/scripts/write-final-report.sh` wires them together. This design (a) records the as-built architecture and acceptance criteria the feature should have shipped with, and (b) closes the one real coverage gap: the degraded-fallback renderer branch that formats bucketed line counts is never asserted.

Round 1 decisions: document-only for timeout posture (no hardening code); the new test belongs in `skills/implement/scripts/test-write-final-report.sh` — the issue body misattributes the fallback path to `scripts/test-render-run-summary.sh`, but `LINES_DATA_OK` and `compose_self_fallback` live in `write-final-report.sh`, and the renderer harness already covers both bullet shapes.

## As-built architecture (documentation deliverable)

- `compute-pr-line-counts.sh` KV contract: `LINES_STATUS=ok` (+ `CODE_ADDED`, `CODE_DELETED`, `LOGS_ADDED`, `LOGS_DELETED`), `LINES_STATUS=skipped` (`REASON=no-pr` / `REASON=invalid-repo`), `LINES_STATUS=unavailable` (`REASON=gh-failed`). Always exit 0 — metrics are never run-fatal.
- Bucketing rule: paths under `larch-logs/` count as logs; everything else (including renames and 0/0 binary rows) counts as code.
- Pagination: single `gh api --paginate` call against `repos/<repo>/pulls/<N>/files` (placeholder endpoint `repos/{owner}/{repo}/...` when `--repo` is empty so gh resolves repo context).
- Input validation: `PR_NUMBER` must be all digits (empty/`0`/non-numeric → `skipped`/`no-pr`); `REPO` is guarded as a single-slash value with non-empty owner and repo parts (extra slash or missing part → `skipped`/`invalid-repo`), not a broader GitHub slug validator. Both values pass to `gh` as argv only — no eval or string-interpolated command surface.
- Integration: `write-final-report.sh` skips the helper entirely when `REPO_UNAVAILABLE=true`, parses the KV blob, derives `LINES_DATA_OK` (all four counters present and numeric), and forwards `--code-added/--code-deleted/--logs-added/--logs-deleted` to `render-run-summary.sh` only when true. The renderer independently re-validates and renders `N/A` otherwise. A two-stage degradation chain follows: renderer failure → retry with `--cost-unavailable` → `compose_self_fallback` (inline body with degraded banner + `larch:final-summary-fallback` marker).
- Timeout posture (documented limitation, per Round 1): the `gh api` call has no explicit timeout and no repo-wide gh-timeout convention exists; a network-level hang would stall `write-final-report.sh`. Accepted as-is — failures observed in practice are fast non-zero exits handled by the `gh-failed` path.

## Files to modify/create

### UPDATED: `skills/implement/scripts/test-write-final-report.sh`

Add one dedicated stage2-fallback test case exercising the `LINES_DATA_OK=true` branch of `compose_self_fallback`:

- New fixture dir (e.g. `impl-lines-fb`): `parent-issue.md` with issue + run id, `session-env.sh` with `REPO=owner/repo`, `ship-pr-state.sh` with a real `PR_NUMBER` (so the existing global `gh` shim returns the deterministic 5-row file fixture → code +17/-3, larch-logs +5/-1) and `MERGE_RESULT=merged`, plus `finalize-state.sh`.
- Replace `render-run-summary.sh` with the existing always-`exit 1` stub pattern so both render attempts fail and `compose_self_fallback` fires; restore the saved real renderer immediately after the case (same save/restore pattern the existing stage2 tests use).
- Assertions: degraded banner present; `larch:final-summary-fallback v1` marker present; exact formatted bullet `- **Lines (PR diff)**: code +17/-3, larch-logs +5/-1` present (the previously untested true-branch printf); PR bullet present (non-zero `PR_NUMBER` in fallback output).

### UPDATED: `skills/implement/scripts/test-write-final-report.md`

Extend the coverage sentence to name the degraded-fallback bucketed line-count case (no hardcoded counts, per drift-prone-prose rule).

## Approach

Smallest change that closes the gap: one new self-contained test case plus its harness-doc sentence. No production-code edits; no renderer-harness edits; no new conventions. The plan body above doubles as the retroactive feature documentation required by issue item 1.

## Edge cases

- The global `gh` shim matches any `pulls/<N>/files` endpoint, so any non-zero numeric `PR_NUMBER` works; pick one not used by other fixtures for log clarity.
- Renderer stub save/restore must bracket only this case so subsequent tests see the real renderer (existing `render-run-summary.real` copy already exists in the harness; reuse it).
- `execution-issues.md` in a fresh fixture dir starts absent; the fallback path appends warnings there — assert on summary body only, not warning counts, to keep the case insensitive to warning-count drift.

## Failure modes

- Shim-fixture drift: if the shared 5-row gh fixture changes, the expected `+17/-3, +5/-1` sums break. Mitigation: the sums are already pinned by the happy-path assertion in this same harness, so drift surfaces in two places at once and is unambiguous.
- Stub leakage: failing to restore the real renderer would cascade failures into later cases. Mitigation: restore immediately after the case's assertions, mirroring the existing stage2 pattern.
- Misattributed-file regression: a future reader following the issue text might re-add a redundant renderer-harness case. Mitigation: this plan and the issue plan block record the corrected target file.

## Testing strategy

- Run `bash skills/implement/scripts/test-write-final-report.sh` — PASS count increases; new case passes; all existing cases unchanged.
- Run `bash scripts/relevant-checks.sh` (or `make lint`) for repo-wide hook coverage.

## Acceptance


1. Integration: `write-final-report.sh` renders bucketed counts when `LINES_STATUS=ok` and all four counters are numeric, and renders `N/A` on `skipped`, `unavailable`, or `REPO_UNAVAILABLE=true` — pinned by existing write-final-report harness cases (happy path, no-PR, repo-unavailable, gh-failed). Partial/non-numeric line-count flags are renderer-contract coverage, pinned in `scripts/test-render-run-summary.sh`, not claimed as write-final-report integration coverage.
2. Pagination: the files request uses `gh api --paginate` (flag presence test-pinned); multi-page PRs aggregate via a single awk pass. Documented limitation: the GitHub `pulls/files` API caps listings at 3000 files; beyond that, counts reflect the API-returned subset.
3. Timeout: no explicit request timeout (documented limitation, accepted in Round 1); all observed failure modes exit non-zero fast and degrade to `LINES_STATUS=unavailable` → `N/A` render, never failing the run.
4. Security validation: digits-only `PR_NUMBER` guard is test-pinned; `REPO` validation is the current single-slash/non-empty-parts guard, with the extra-slash invalid case pinned and no claim of full GitHub slug validation. Inputs reach `gh` as argv only.
5. Fallback coverage (the new work): `compose_self_fallback` formats `Lines (PR diff)` from bucketed values when `LINES_DATA_OK=true` — asserted by the new stage2-fallback case; the N/A arm remains pinned by the existing bailed-fixture schema test.
6. Harness doc sibling updated in the same PR.

diff_lines: 47

## Test plan
(no test plan section in plan-file)
