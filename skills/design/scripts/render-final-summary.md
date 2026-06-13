# render-final-summary.sh

**Allowlist validation**: Sources `scripts/lib-design-tmpdir.sh` and calls `larch_design_tmpdir_validate "$DESIGN_TMPDIR"` after the required-env check and before any tmpdir reads; failure maps to exit `$?` (env-based `DESIGN_TMPDIR` consumers use raw exit rather than a KV-emitting wrapper).

**Purpose**: `/design` terminal summary dispatcher. Gathers token/timing JSON,
parses `execution-issues.md`, `voting-tally.md`, accepted findings, and OOS URLs,
then composes `review-findings-full.jsonl`, renders the best-effort Review Phase
Detail appendix, invokes `scripts/render-run-summary.sh --skill design`, and
(post-publish phase) prints the body to chat and upserts `<!-- larch:final-summary v1 runid=… -->`
via `python3 python/cli.py tracking-issue upsert-summary` **internally** (SKILL.md references only
this helper).

## Callers (twelve)

Step 0b title-filter refuse (`cancelled-title-filter`), clarify exit, already-planned cancel, reentry-guard cancel
(`cancelled-reentry-guard`); Step 1c/1d sprawl
cancel; Step 1d.7 outline cancel (`cancelled-outline`); Step 2b.5 hard cancel; Step 2b.5 Split-path terminal cancels / successful
partition filing (`cancelled-decompose`, `approved-partition`); Step 5c happy path (`--post-publish-only` after
the publish outcome is known); Step 5c plan-block-write failure (`--outcome
failed-plan-write`), and log-publish failure after Gate-C approval (`--outcome
failed-publish`). The current `design-publish.sh` success path orders Step 5c as
plan write → diagram upsert → `[DESIGNED]` rename → design-log publish →
`--post-publish-only` final-summary render → reentry marker.

The shell enum keeps file-order with newest cancelled entries appended before the `failed-*` outcomes; `SKILL.md` Step 0b documents the same token set alphabetically within `cancelled-*`.

## Split-path / pre–Step 0a

Step 2b.5 Split-path calls this helper on **`SUMMARY_OUTCOME=approved-partition`** and **`SUMMARY_OUTCOME=cancelled-decompose`** terminal exits (same `### Final summary block` fence as other single-phase cancels). Other Split-path branches preserve `$DESIGN_TMPDIR` without invoking `render-final-summary.sh` until a terminal outcome is chosen.
Pre–Step 0a aborts have no `$DESIGN_TMPDIR`.

## Publish-tail render behavior

`design-publish.sh` removes any stale `final-summary.md`, writes the plan block,
best-effort upserts the architecture diagram, attempts the `[DESIGNED]` rename,
then invokes `design-log-publish.sh`. It exports the publish metadata and rename
admission hint (`RENAMED`, `NEW_TITLE`, `DESIGNED_ADMISSION_READY`) before
rendering the terminal summary with `--post-publish-only`, so failed-publish
notes can distinguish "logs still need recovery but /implement may proceed" from
"fix the issue title before /implement". If the post-publish render fails or
leaves the file empty, the helper appends a Warning and writes the self-composed
fallback schema. On post-phase failures it refreshes `Exec issues` / `Warnings`
from `execution-issues.md` and only carries forward the prior non-`N/A`
`- **Cost**:` line when one already existed; it does not preserve the rest of a
stale body.

## Cost unavailable (FINDING_12)

When token JSON is missing/unparseable, or all parsed token counts are zero, the
helper passes
`--cost-unavailable` into `render-run-summary.sh`, yielding `- **Cost**: N/A`
(not a misleading `$0.00`). Passing no token flags is not sufficient because the
shared renderer defaults omitted counts to zero. The token-count sourcing
includes the spawned-process Claude lane (`Claude (subprocess)` / `claude_sub`,
issue #3637): the helper reads `.claude_sub.totals.total` and
`BUCKETS_claude_sub` from `token-report-final.json` and forwards `--claude-sub-*`
flags to the renderer.

## Review Phase Detail appendix

Before invoking `render-run-summary.sh`, `invoke_render()` removes stale
`review-phase-detail.md`, prepares a valid rounds root, removes stale
`review-findings-full.jsonl`, calls
`scripts/compose-review-findings.sh --design-artifacts-dir`, and then calls
`scripts/render-review-phase-detail.sh --skill design` with `--rounds-root`,
`--findings-file`, `--timing-ledger`, optional `--token-ledger`, and `--output`.
When `$DESIGN_TMPDIR/plan-review` is absent, it creates that directory as an
empty rounds root so the shared renderer can emit `## Review Phase Detail` plus
`No review rounds completed.`. If preparing that root fails, the helper keeps the
prior best-effort empty behavior. Final summaries do not pass `--no-gantt`, so
reviewer timing ASCII Gantt charts appear when timing data is available. Valid roots
with zero completed rounds render `No review rounds completed.`. Live terminal
progress may skip the shared renderer when every discovered round dir lacks
`round-meta.json`; this final-summary helper does not apply that skip. Compose/render
failures truncate the relevant intermediate and continue. The compose path owns
cumulative `accepted-plan-findings-all.md` precedence, Gate B skipped-finding
filtering, and reviewer-slot basename normalization. The calls are best-effort
and do not toggle global `errexit`.

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
`python/cli.py run-log verify-completeness` and
`python/cli.py audit-runs scan-run` keep anchoring on the
terminal outcome. Fallback still exits 0, and Warning recording through
`run-log append-failure` is unchanged; the banner says "execution issues"
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

## Plan review line counting

The Plan review line counts `### FINDING_N:` blocks in `accepted-plan-findings-all.md` when present, otherwise `accepted-plan-findings.md`, and `### OOS_N:` blocks in `oos-accepted-design.md` directly (header presence, not `focus-area` text matching). When Gate B one-by-one review explicitly skipped findings, matching skipped blocks from `rejected-findings.md` are excluded from the cumulative accepted count. Missing optional files are omitted from the awk input list rather than passed as unreadable paths. Per-bucket breakdown uses `- **Focus area**: <value>` (bold, capital F, colon) when present; blocks without a matching Focus area line fall to the `low` bucket via an end-of-awk fallback. Prior to this fix the regex matched `- focus-area = <value>` which never appeared in production artifacts, causing the count to always be 0.

Counting is not gated on `voting-tally.md`; cap-reached cleanup can remove the
round-local tally while leaving cumulative accepted artifacts intact, and the
final summary must still report those accepted findings.

## OOS filed sentinel fallback

When `$DESIGN_TMPDIR/oos-issues-created.md` is absent or empty but `$DESIGN_TMPDIR/oos-issue-sentinel` exists with `ISSUES_CREATED >= 1` and `ISSUES_FAILED = 0`, the helper reads `ISSUES_CREATED` from the sentinel and reports `OOS filed: N — (URLs unavailable — annotate step was skipped)` rather than silently showing `0`. Sentinels with `ISSUES_FAILED > 0` are treated as partial failures and not used for the count, so stale or partial-failure sentinels do not inflate the OOS filed count. This covers cases where `/issue` ran (creating the sentinel) but `file-design-oos.sh annotate` was never called (so `oos-issues-created.md` was never written).

## Recent contract coverage

- `publish-skipped` is an accepted outcome with an explicit Outcome bullet, a skipped-publish note, no failed-publish recovery prose, and `Run logs` left as `N/A`.
- Plan review line now counts cumulative `### FINDING_N:` / `### OOS_N:` headers directly with `- **Focus area**: <value>` buckets; `test-render-final-summary.sh` covers non-zero accepted sets, missing optional OOS artifacts, cumulative accepted sets, Gate B skipped cumulative findings, and cumulative accepted sets after `voting-tally.md` removal. Review Phase Detail wiring is covered through the compose and renderer harnesses plus plan-review-loop metadata tests.

## Invariants

- Reads `bg-poll-guard-denials.count`; positive counts append a warning and render a `Blocked polling attempts` note.
