# render-final-summary.sh

**Purpose**: `/design` terminal summary dispatcher. Gathers token/timing JSON,
parses `execution-issues.md`, `voting-tally.md`, accepted findings, and OOS URLs,
then invokes `scripts/render-run-summary.sh --skill design` and (post-publish
phase) prints the body to chat and upserts `<!-- larch:final-summary v1 runid=… -->`
via `scripts/tracking-issue-summary.sh` **internally** (SKILL.md references only
this helper).

## Callers (ten)

Step 0b title-filter refuse (`cancelled-title-filter`), clarify exit, already-planned cancel, tier-gate cancel; Step 1c/1d sprawl
cancel; Step 2b.5 hard cancel; Step 2b.5 Split-path terminal cancels / successful
partition filing (`cancelled-decompose`, `approved-partition`); Step 5c happy path (two-phase: `--pre-publish-only`
before `design-log-publish.sh`, `--post-publish-only` after); Step 5c
plan-block-write failure (`--outcome failed-plan-write`).

## Split-path / pre–Step 0a

Step 2b.5 Split-path calls this helper on **`SUMMARY_OUTCOME=approved-partition`** and **`SUMMARY_OUTCOME=cancelled-decompose`** terminal exits (same `### Final summary block` fence as other single-phase cancels). Other Split-path branches preserve `$DESIGN_TMPDIR` without invoking `render-final-summary.sh` until a terminal outcome is chosen.
Pre–Step 0a aborts have no `$DESIGN_TMPDIR`.

## Two-phase drift trade-off

Phase 1 writes `final-summary.md` before `design-log-publish.sh` so the design
log commit can bundle it. Phase 2 re-renders after publish (success or failure) so
GitHub upsert and chat match post-publish warnings. The committed Phase-1 file
may differ slightly from the Phase-2 body when publish appends warnings; a
second commit to refresh the log bundle is intentionally not required.

## Cost unavailable (FINDING_12)

When token JSON is missing/unparseable, or all per-bucket counts are zero **and**
`token-report-final.stderr.log` is non-empty, the helper passes **no** token
flags into `render-run-summary.sh`, yielding `- **Cost**: N/A` (not a misleading
`$0.00`).

## Exec issues / warnings (FINDING_13)

Counts `**Step` lines under `### Tool Failures`, `### External Reviewer Issues`
(combined into `--exec-issues`), and `### Warnings` separately.

## Upsert gate

Upsert runs when `ISSUE_NUMBER` is non-empty and the rendered body is non-empty,
independent of `PLAN_WRITE_OK` (publish/rename remain gated separately in SKILL.md).
