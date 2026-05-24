## Goal
Fix four stale documentation surfaces (cost-line contract, outcome enumeration, run-logs sentinel semantics) and one Bash 3.2 portability regression in render-final-summary.sh

## Implementation Plan
## Plan

## Goal

Fix three stale documentation surfaces that drifted from the current code contract after PR #2714 (run-summary consolidation), PR #2629 (token-cost pipeline), and #2579 (`/fix-issue` skill removal), **plus** one Bash 3.2 portability regression in the new `/design` final-summary renderer:

1. Cost-line contract: docs implying `token-report.sh --summary` is a "dollar summary" and that `scripts/token-cost.sh` has `/fix-issue` callers.
2. Outcome enumeration: prose claiming `render-run-summary.sh` emits the `Outcome` bullet only for `stalled` / `bailed*`, when it also emits for `cancelled-*` / `failed-*`.
3. `/implement`-only sentinel semantics in `docs/run-logs.md` for `final-summary.md`, when `/design` now produces the same artifact and upserts the same `larch:final-summary` tracking comment.
4. `skills/design/scripts/render-final-summary.sh` fails on macOS system Bash 3.2 with `print_arg[@]: unbound variable` whenever the optional `--print-stdout` arg array is empty under `set -euo pipefail`. Discovered when running `/design --trivial 2743` itself: both the `--pre-publish-only` and `--post-publish-only` callsites hit it. Per `BASH_AUTHORING.md` §3 the repo's shell scripts must stay Bash-3.2-compatible.

The implementation is mostly a documentation patch plus one small script-portability fix.

## Files to modify/create

### UPDATED: `scripts/token-report.md`

Stale claim near the top of the file (in the "Relationship to scripts/token-tally.md" paragraph): "Dollar summaries (`--summary`, markdown cost surfaces) delegate to `scripts/token-cost.sh` via the same per-bucket counts as JSON `BUCKETS_*` when available."

Current contract:
- `token-report.sh --summary` emits a **non-dollar** `Tokens:` rollup line (pinned by `scripts/test-token-report-summary-format.sh`, which fails on `💰 Cost:`).
- The dollar `- **Cost**:` bullet lives in `scripts/render-run-summary.sh` only; the markdown JSON output (`--full --format json`) carries `BUCKETS_*` counts that `token-cost.sh` consumes.

Replacement wording must:
- Remove the implication that `--summary` is a dollar surface.
- Keep the genuine relationship: the markdown / JSON `--full` outputs expose per-bucket counts that `token-cost.sh` consumes when rendering the dollar `- **Cost**:` bullet via `render-run-summary.sh`.
- Stay consistent with the existing `--summary` description further down in the "Subcommands" section ("non-dollar token rollup line for chat breadcrumbs ... dollar-primary cost line ... lives exclusively in `scripts/render-run-summary.sh`").

### UPDATED: `scripts/token-cost.md`

Two stale `/fix-issue` references after PR #2579 removed that skill:
- Header paragraph: "...and by the `/fix-issue` helpers."
- "Note on `/research`" table, "Primary skills / workflows" row: lists `/fix-issue` alongside `/implement` and `/design`.

Replacement scope:
- Remove the `/fix-issue` mention from the header paragraph and from the table cell.
- Preserve the genuine consumers: `/implement` and `/design` (via `scripts/render-run-summary.sh`), plus the deprecation note that `render-cost-line` has no in-flow skill callers after PR #2714.

### UPDATED: `skills/implement/scripts/write-final-report.md`

Stale prose in the opening paragraph: "The renderer emits `- **Outcome**:` only for `stalled` or outcomes beginning with `bailed`..."

Current contract (verified against `scripts/render-run-summary.sh` outcome case statement): the renderer emits the bullet for `bailed*`, `stalled`, `cancelled-*`, and `failed-*`. The expanded set lands when `/design` runs render the shared summary; `/implement` itself still only emits the nine outcomes already enumerated in the "Implement outcome enum" section below the paragraph, so the enum list is unchanged.

Replacement scope:
- Update the renderer-behavior sentence to enumerate all four outcome patterns.
- Leave the nine-value `/implement` outcome enum and the per-outcome computation rules untouched (those remain `/implement`-specific and current).

### UPDATED: `docs/run-logs.md`

Two drifts in the `### final-summary.md` block:

- "Step 8+ before PR creation and refreshed later by terminal summary paths" is `/implement`-only framing. After PR #2714, `/design` also writes `larch-logs/design/<RUN_ID>/final-summary.md` (via `skills/design/scripts/render-final-summary.sh`) and upserts the same `larch:final-summary` tracking-issue comment. The section needs to acknowledge both skills.
- Renderer-behavior sentence mirrors the stale claim in `write-final-report.md`: "`- **Outcome**:` only for `stalled` / `bailed*` outcomes". Update to enumerate `stalled`, `bailed*`, `cancelled-*`, `failed-*`.

Replacement scope:
- Generalize the **Written** mode line so both skills are covered (point at `scripts/render-run-summary.sh` for the rendered body and at the per-skill writers — `write-final-report.sh` for `/implement`, `render-final-summary.sh` for `/design` — for the write/upsert lifecycle, rather than naming a single `/implement` step number).
- Update the renderer-behavior sentence to list all four outcome patterns.
- Keep the rest of the section (bullet contract, PR-bullet omission rules, sentinel marker, tracking-comment projection) intact.

### UPDATED: `docs/linting.md`

Issue body lists this file under sub-task 1 (cost-line contract). Direct inspection of the file shows the relevant rows already match the current contract:

- The `test-render-run-summary-format` row already says "single `- **Cost**:` bullet with dollar-primary line".
- The `test-token-report-summary-format` row already says "non-dollar `Tokens:` + per-vendor line (no `💰 Cost:`)".

No stale prose remains in this file. The file is listed in the plan for completeness (so the implementer touches the issue's full claimed surface) but no diff is expected; if the implementer finds residual drift the verification did not catch, they apply the same non-dollar-`--summary` / dollar-`render-run-summary.sh` distinction used in the other two files above.

### UPDATED: `skills/design/scripts/render-final-summary.sh`

Bash 3.2 + `set -euo pipefail` + empty `print_arg=()` array → `print_arg[@]: unbound variable` at the two `render-run-summary.sh` invocation sites inside `invoke_render()`. Reproducible on macOS system Bash by running `/design --trivial <issue>` end-to-end; the `--pre-publish-only` call hits the empty-array branch (no `--print-stdout`) and the `--post-publish-only` call hits the same branch when `COST_ARGS` is also empty.

Fix scope:
- Replace each of the two `"${print_arg[@]}"` expansions inside `invoke_render()` with the standard Bash 3.2 empty-array guard: `${print_arg[@]+"${print_arg[@]}"}`. This is the same pattern `BASH_AUTHORING.md` §3 already recommends, and it has no semantic effect on Bash 4+.
- Audit the rest of the file for any other `${arr[@]}` expansions of arrays that may be empty under `set -u`; apply the same guard if any are found. The expected count is two — both inside `invoke_render()` — but the audit is the safer scope.

This file lives under `skills/`, so it counts as part of the **runtime plugin authority surface** per `AGENTS.md`. The change is a true scripting fix, not docs polish.

## Approach

- Documentation patch across four `.md` files plus one Bash 3.2 portability fix in `skills/design/scripts/render-final-summary.sh`. No behavior, schema, or CI changes beyond exercising `make lint-bash32`.
- Each file is edited in isolation; the changes do not interact. The script fix and the docs edits do not share any state.
- Wording in the doc edits must match terminology already used elsewhere in the same files (the existing "Subcommands" section of `token-report.md` and the renderer's own case statement are the canonical templates).
- The script fix must match the empty-array guard documented in `BASH_AUTHORING.md` §3 verbatim (`${arr[@]+"${arr[@]}"}`); do not invent a different idiom.
- Per `.claude/rules/drift-prone-prose-in-docs.md`: do not pin line numbers in the new prose, do not paste machine-local paths, and do not write hard-coded counts that will rot. Refer to outcome patterns by their literal shell-glob shape (`bailed*`, `cancelled-*`, `failed-*`) and to functions / sections by name.

## Edge cases

- **`docs/linting.md` no-op**: if the verification confirms no remaining drift, the file produces zero diff. The implementer should not invent changes to "match" the issue body; report the no-op in the PR description.
- **Future drift after this PR**: the renderer's outcome filter is the source of truth (`scripts/render-run-summary.sh` case statement). If a later PR extends or narrows the filter, every doc enumeration must be re-synced.
- **`/research`-only divergence**: the existing `Note on /research` block in `token-cost.md` correctly contrasts `token-cost.sh` and `token-tally.sh`. Only the row cell that lists primary skills changes; the rest of the table stays.
- **Bash 3.2 coverage**: CI's runners may use Bash 4+ where the empty-array expansion would not trip. The guard pattern is a no-op on Bash 4+, so the fix is unconditionally safe. `make lint-bash32` (per `BASH_AUTHORING.md` §3) is the local gate against re-introducing the same class of bug elsewhere.
- **Local plugin cache vs. source tree**: the `/design` run that filed this amendment patched the LOCAL plugin cache copy (`~/.claude/plugins/cache/larch-local/larch/<ver>/skills/design/scripts/render-final-summary.sh`) so finalization could complete. The implementer must apply the same fix to the in-tree authoritative copy under `skills/design/scripts/`; the plugin cache will be refreshed automatically when the next plugin version ships.

## Testing strategy

No new test files. The relevant pins already exist:
- `scripts/test-token-report-summary-format.sh` (asserts no `💰 Cost:` in `--summary`).
- `scripts/test-render-run-summary.sh` and `scripts/test-render-run-summary-format.sh` (assert dollar `- **Cost**:` bullet in the rendered summary).
- The outcome case statement in `scripts/render-run-summary.sh` is exercised by `scripts/test-render-run-summary.sh`.
- `make lint-bash32` (per `BASH_AUTHORING.md` §3) blocks Bash 4+ constructs in committed shell scripts.

Manual verification after edits:
- `make lint` (catches markdown lint issues, MD038 on inner-whitespace code spans, structural docs-sync probes, and Bash 3.2 portability).
- Run `bash /bin/bash --version` (or `/bin/bash --version`) to confirm Bash 3.2 is the macOS system shell; then exercise `skills/design/scripts/render-final-summary.sh --outcome approved --mode TRIVIAL_DOC_ONLY --pre-publish-only` against a throwaway `$DESIGN_TMPDIR` and verify it exits 0 (was exit 1 with the unbound-variable error before the fix). Re-run the same script with `--post-publish-only` to cover both branches of the `COST_ARGS` conditional inside `invoke_render()`.
- Spot-grep each edited file for the previously stale phrases to confirm removal.

## Diff size estimate

Four files definitely change (`scripts/token-report.md`, `scripts/token-cost.md`, `skills/implement/scripts/write-final-report.md`, `docs/run-logs.md`) plus the two-line guard in `skills/design/scripts/render-final-summary.sh`. One file is a no-op (`docs/linting.md`). Each editable doc change is a sentence or short paragraph reword; the script fix is two single-line edits inside `invoke_render()`. Total expected delta is roughly 10-25 lines across five files.

## Acceptance

- After-state contract changes are reflected in `scripts/token-report.md` (no claim that `--summary` is a dollar surface), `scripts/token-cost.md` (no `/fix-issue` callers in the consumer list), `skills/implement/scripts/write-final-report.md` (renderer-behavior sentence lists `bailed*`, `stalled`, `cancelled-*`, `failed-*`), and `docs/run-logs.md` `### final-summary.md` block (both `/implement` and `/design` are acknowledged; same four outcome patterns).
- `docs/linting.md` already matches the current contract; if no residual drift surfaces during implementation, no diff to that file is acceptable.
- `skills/design/scripts/render-final-summary.sh` runs end-to-end on macOS system Bash 3.2 in both `--pre-publish-only` and `--post-publish-only` modes without `unbound variable` errors. The fix uses the `${arr[@]+"${arr[@]}"}` pattern verbatim; any other `${arr[@]}` expansion of a potentially-empty array in the same file gets the same guard.
- `make lint` passes (markdown lint, structural docs-sync probes, Bash 3.2 portability).
- After the edits, each previously-stale phrase no longer appears in the file it was removed from. Verification phrases (literal — search without quoting):

  ```
  Dollar summaries                                   (scripts/token-report.md — removed)
  /fix-issue                                          (scripts/token-cost.md — removed from header + table)
  only for `stalled` or outcomes beginning with `bailed`   (write-final-report.md — replaced)
  `- **Outcome**:` only for `stalled` / `bailed*`     (docs/run-logs.md — replaced)
  print_arg[@]                                        (render-final-summary.sh — only inside guarded expansions)
  ```

- No code or test changes beyond the two-line script guard; existing pin tests (`scripts/test-token-report-summary-format.sh`, `scripts/test-render-run-summary.sh`, `scripts/test-render-run-summary-format.sh`) remain green without modification.

diff_lines: 22

## Test plan
(no test plan section in plan-file)
