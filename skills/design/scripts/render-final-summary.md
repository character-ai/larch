# render-final-summary.sh

**Allowlist validation**: Sources `scripts/lib-design-tmpdir.sh` and calls `larch_design_tmpdir_validate "$DESIGN_TMPDIR"` after the required-env check and before any tmpdir reads; failure maps to exit `$?` (env-based `DESIGN_TMPDIR` consumers use raw exit rather than a KV-emitting wrapper).

**Purpose**: `/design` terminal summary dispatcher. Gathers token/timing JSON,
parses `execution-issues.md`, `voting-tally.md`, accepted findings, and OOS URLs,
then invokes `scripts/render-run-summary.sh --skill design` and (post-publish
phase) prints the body to chat and upserts `<!-- larch:final-summary v1 runid=… -->`
via `scripts/tracking-issue-summary.sh` **internally** (SKILL.md references only
this helper).

## Callers (twelve)

Step 0b title-filter refuse (`cancelled-title-filter`), clarify exit, already-planned cancel, reentry-guard cancel
(`cancelled-reentry-guard`); Step 1c/1d sprawl
cancel; Step 1d.7 outline cancel (`cancelled-outline`); Step 2b.5 hard cancel; Step 2b.5 Split-path terminal cancels / successful
partition filing (`cancelled-decompose`, `approved-partition`, `cancelled-assessor-worse`); Step 5c happy path (two-phase: `--pre-publish-only`
before `design-log-publish.sh`, `--post-publish-only` after); Step 5c
plan-block-write failure (`--outcome failed-plan-write`), and log-publish failure
after Gate-C approval (`--outcome failed-publish`).

The shell enum keeps file-order with newest cancelled entries appended before the `failed-*` outcomes; `SKILL.md` Step 0b documents the same token set alphabetically within `cancelled-*`.

## Split-path / pre–Step 0a

Step 2b.5 Split-path calls this helper on **`SUMMARY_OUTCOME=approved-partition`** and **`SUMMARY_OUTCOME=cancelled-decompose`** terminal exits (same `### Final summary block` fence as other single-phase cancels). Other Split-path branches preserve `$DESIGN_TMPDIR` without invoking `render-final-summary.sh` until a terminal outcome is chosen.
Pre–Step 0a aborts have no `$DESIGN_TMPDIR`.

## Publish-tail render behavior

`design-publish.sh` removes any stale `final-summary.md` before invoking
`design-log-publish.sh`, then renders the terminal summary after the publish
outcome is known. This avoids committing an approved summary into an open
failed-publish flush PR. If the post-publish render fails or leaves the file
empty, the helper appends a Warning and writes the self-composed fallback
schema. On post-phase failures it refreshes `Exec issues` / `Warnings` from
`execution-issues.md` and only carries forward the prior non-`N/A`
`- **Cost**:` line when one already existed; it does not preserve the rest of a
stale body.

## Cost unavailable (FINDING_12)

When token JSON is missing/unparseable, or all parsed token counts are zero, the
helper passes
`--cost-unavailable` into `render-run-summary.sh`, yielding `- **Cost**: N/A`
(not a misleading `$0.00`). Passing no token flags is not sufficient because the
shared renderer defaults omitted counts to zero.

## Degraded render — fallback

`render-run-summary.sh` is invoked to write `final-summary.md` only. If it exits
non-zero or leaves the file empty, this helper appends a Warning to
`execution-issues.md`, refreshes counts, and writes a self-composed `/design`
schema body: conditional `- **Outcome**:` for cancelled/failed outcomes, no PR
bullet, no Code review bullet, and the
`<!-- larch:run-summary v=1 -->` sentinel. The fallback uses `- **Cost**: N/A`
unless post phase already had a usable cost line, in which case only that line
is preserved.

The self-composed fallback body is intentionally distinguishable from a full
renderer body: it places `**⚠ Degraded fallback — full renderer failed; warning
recorded in execution issues.**` immediately after the `## /design run ...`
heading, with one blank line on each side, and emits
`<!-- larch:final-summary-fallback v1 -->` directly after the existing
`<!-- larch:run-summary v=1 -->` marker. The heading remains the first
non-empty line so first-line outcome parsers in
`scripts/verify-run-log-completeness.sh` and
`.claude/skills/audit-runs/scripts/audit-scan-run.sh` keep anchoring on the
terminal outcome. Fallback still exits 0, and Warning recording through
`append-tool-failure.sh` is unchanged; the banner says "execution issues"
without a filename because design tmpdirs use `execution-issues.md` while
published implement logs use `execution-issues.ndjson`.

## PHASE=post print path

Post phase prints `final-summary.md` exactly once via the FD-3-aware chat loop.
The renderer itself is not called with `--print-stdout`, so the file and chat
body share one source and fallback bodies are printed through the same path.

## Exec issues / warnings (FINDING_13)

Counts `- **Step` lines under `### Tool Failures`, `### External Reviewer Issues`
(combined into `--exec-issues`), and `### Warnings` separately.

## Upsert gate

Upsert runs when `ISSUE_NUMBER` is non-empty and the rendered body is non-empty,
independent of `PLAN_WRITE_OK` (publish/rename remain gated separately in SKILL.md).
