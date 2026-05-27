## Plan

# Implementation Plan — #3053 Distinguishable degraded-fallback final-summary.md

## Overview

`compose_self_fallback` in `skills/design/scripts/render-final-summary.sh` (line 358) and the structurally identical function in `skills/implement/scripts/write-final-report.sh` (line 443) emit a `final-summary.md` whose body is indistinguishable from a successful rich render. When `invoke_render` / `run_body_render` fails, the fallback file lacks any in-body signal, the script still exits 0, and downstream consumers (notably the SKILL.md "shared post-publish full-body emit" rule that re-emits the file verbatim to chat) treat the fallback as a full render. The accompanying `append_render_warning` does already append a `Warnings` entry to the execution-issues log (`execution-issues.md` in design tmpdirs, `execution-issues.ndjson` in committed implement run logs), so the failure is logged — but readers of `final-summary.md` itself cannot tell whether the document they are looking at is full or degraded.

Insert a two-part marker into the fallback body in both scripts:

1. A loud visible banner line `**⚠ Degraded fallback — full renderer failed; warning recorded in execution issues.**` placed immediately AFTER the `## ... run <RUN_ID> — <OUTCOME>` heading. The exact sequence is: heading line, one blank line, banner line, one blank line, then the existing bullet list. The banner text is intentionally artifact-neutral (no `.md` suffix) because design tmpdirs use `execution-issues.md` while committed implement run logs use `execution-issues.ndjson`; a single message points readers to whichever surface their context exposes.
2. An HTML comment marker `<!-- larch:final-summary-fallback v1 -->` placed on its own line directly after the existing `<!-- larch:run-summary v=1 -->` marker.

Exit code stays 0 (no caller-contract change). Banner placement is constrained to NOT precede the heading because `scripts/verify-run-log-completeness.sh` (`final_summary_heading_bail_signal`) and `.claude/skills/audit-runs/scripts/audit-scan-run.sh` (`_rf_check_terminal_outcome`) anchor on the first non-empty line matching `RUN_LOG_TERMINAL_OUTCOME_SUFFIX_EGREP` from `scripts/run-log-terminal-outcomes.inc.bash`.

## Files to modify/create

### UPDATED: `skills/design/scripts/render-final-summary.sh`

Inside `compose_self_fallback()` (lines 358-390):

- After the `printf '## /design run %s — %s\n\n' "$RUN_ID" "$OUTCOME"` heading line (line 361), add `printf '%s\n\n' '**⚠ Degraded fallback — full renderer failed; warning recorded in execution issues.**'` so the body sequence is heading-line / blank / banner / blank / first bullet.
- After the `printf '%s\n' '<!-- larch:run-summary v=1 -->'` line (line 385), add a sibling `printf '%s\n' '<!-- larch:final-summary-fallback v1 -->'` so both markers appear adjacent.
- Do NOT change `invoke_render`, `render_or_fallback`, `append_render_warning`, `refresh_issue_counts`, `restore_preserved_cost_line`, exit code, or the existing `<!-- larch:run-summary v=1 -->` marker. Do NOT touch the cancelled-outline `Cancel site` bullet (line 386-388) — its placement after the markers is unchanged; the new fallback marker sits between the existing run-summary marker and the cancel-site bullet.

### UPDATED: `skills/implement/scripts/write-final-report.sh`

Inside `compose_self_fallback()` (lines 443-483):

- After the `printf '## /implement run %s — %s\n\n' "$RUN_ID" "$OUTCOME"` heading line (line 445), add `printf '%s\n\n' '**⚠ Degraded fallback — full renderer failed; warning recorded in execution issues.**'`. Use the identical banner text as the design-side change.
- After the `printf '%s\n' '<!-- larch:run-summary v=1 -->'` line (line 477), add `printf '%s\n' '<!-- larch:final-summary-fallback v1 -->'`.
- Do NOT change the Stage-1 `run_body_render` retry or the Stage-2 `run_body_render "$notes_tmp" true` `--cost-unavailable` retry (lines 496-505); those stages produce a real render-run-summary body and are already distinguished by `- **Cost**: N/A`. Only the terminal Stage-3 `compose_self_fallback` path (line 503) gets the marker.
- Do NOT change exit code, `run_body_render`, `append_render_warning`, or the existing `<!-- larch:run-summary v=1 -->` marker.

### UPDATED: `skills/design/scripts/test-render-final-summary.sh`

EXTEND the existing renderer-failure / fallback block (around lines 206-225, the block that already validates renderer-fail post-path preserved cost line, title refresh, exec/warning counts) — do NOT add a new top-level test case. The block already triggers the renderer failure and inspects `$D/final-summary.md`; piggyback the new assertions there.

Add these assertions inside that existing block:

1. `grep -Fq -- '**⚠ Degraded fallback' "$D/final-summary.md" || fail '...'` — banner substring present (substring is enough; do not pin the entire banner line).
2. `grep -Fq -- '<!-- larch:final-summary-fallback v1 -->' "$D/final-summary.md" || fail '...'` — new HTML marker present.
3. `grep -Fq -- '<!-- larch:run-summary v=1 -->' "$D/final-summary.md" || fail '...'` — existing HTML marker still present (regression guard against accidental replacement).
4. **Strict placement assertion**: read the first 4 non-empty lines of `$D/final-summary.md` and assert the sequence is `## /design run RUN-FB — approved` (line 1), banner-line containing `**⚠ Degraded fallback`, then the first bullet (`- **Mode**:` or `- **Outcome**:`). Implementation can use `awk` / `sed` to skip blank lines and grab the first two non-empty lines, then test that line 1 starts with `## /design run ` and line 2 starts with `**⚠ Degraded fallback`. This directly verifies the heading-then-banner adjacency required by the design.
5. Reuse the existing block's exit-code assertion implicitly — that block already runs the script and checks output content; no new exit-code assertion is needed if the existing block does not bail on the script's rc.

If the existing block tests both `--pre-publish-only` and `--post-publish-only` variants, the new assertions only need to run on whichever variant the fallback path produces an explicit `compose_self_fallback`-shape body (the post variant is the typical sentinel-write path; pre may also write the file but with the same fallback marker if the renderer fails).

### UPDATED: `skills/implement/scripts/test-write-final-report.sh`

EXTEND the existing `renderer fallback stage2` block (around lines 364-385, the block that already asserts ordered implement schema, no PR bullet, Warnings section, etc.) — do NOT add a new top-level test case. Stage 2 in the implement harness's naming corresponds to the terminal `compose_self_fallback` path because the harness's stub renderer fails twice (Stage-1 primary + Stage-1 `--cost-unavailable` retry) before falling through.

Add these assertions inside that existing block:

1. `assert_contains '**⚠ Degraded fallback' "$fallback_stage2" 'renderer fallback stage2 emits degraded banner'`
2. `assert_contains '<!-- larch:final-summary-fallback v1 -->' "$fallback_stage2" 'renderer fallback stage2 emits fallback HTML marker'`
3. Existing `assert_contains '<!-- larch:run-summary v=1 -->' "$fallback_stage1" 'renderer fallback stage1 keeps sentinel'` should also hold for stage2 — extend if not already asserted there.
4. **Strict placement assertion**: extract the first 2 non-empty lines of `$fallback_stage2` (use a small awk extractor — the harness already does `printf '%s\n' "$body" | awk ...` for `assert_schema_ordered`); assert line 1 starts with `## /implement run ` and line 2 starts with `**⚠ Degraded fallback`. This verifies heading-then-banner adjacency.
5. Implicitly assert NO marker appears in `fallback_stage1` (stage1 is the `--cost-unavailable` retry that succeeded — should NOT carry the degraded-fallback banner). Add `assert_not_contains '<!-- larch:final-summary-fallback v1 -->' "$fallback_stage1" 'stage1 must not carry degraded-fallback marker'` and `assert_not_contains '**⚠ Degraded fallback' "$fallback_stage1" 'stage1 must not carry degraded-fallback banner'`. This regression-guards FINDING_3's stage-discrimination invariant.

### UPDATED: `skills/design/scripts/render-final-summary.md`

Document the new fallback contract:

- Add a short subsection (e.g., under the existing "Fallback rendering" or "Output contract" area) noting that on `invoke_render` failure, the locally-composed fallback body now includes (a) a visible bold-warning banner immediately after the heading and (b) an `<!-- larch:final-summary-fallback v1 -->` HTML comment adjacent to the existing `<!-- larch:run-summary v=1 -->` marker.
- State the placement invariant: the banner is placed AFTER the heading line, with one blank line on each side, so first-non-empty-line audit parsers (`scripts/verify-run-log-completeness.sh`, `.claude/skills/audit-runs/scripts/audit-scan-run.sh`) continue to anchor on the outcome heading.
- Note that the script exit code is unchanged (still 0 on fallback) and the `Warnings` entry in `execution-issues.md` (via `append-tool-failure.sh`) is unchanged. The banner text is intentionally artifact-neutral ("warning recorded in execution issues") because design tmpdirs use `execution-issues.md` while committed implement run logs use `execution-issues.ndjson`.

### UPDATED: `skills/implement/scripts/write-final-report.md`

Mirror the same documentation in the implement-side sibling: banner + HTML comment in Stage-3 terminal `compose_self_fallback` only; Stage-1 / Stage-2 retry paths are unchanged; exit code unchanged. Explicitly note that the Stage-2 `--cost-unavailable` body must NOT carry the degraded-fallback marker (the test harness regression-guards this).

## Approach

The change is the smallest possible: 4 surgical edits in 2 scripts (heading-adjacent `printf` plus marker-adjacent `printf`) and extensions to 2 existing harness blocks plus 2 sibling-.md updates. No new helper functions, no new variables, no new top-level test cases, no caller changes, no SKILL.md changes (SKILL.md already states "shared post-publish/full-body emit rule runs only when the helper exited 0 and `$DESIGN_TMPDIR/final-summary.md` is non-empty" — both still hold; the body now self-describes its degraded state).

The HTML comment marker `<!-- larch:final-summary-fallback v1 -->` follows the established `<!-- larch:run-summary v=1 -->` convention. The `v1` version suffix is included so future shape changes can bump the version without breaking grep-based audit tooling.

## Edge cases

- **`cancelled-outline` outcome (design-side only)**: `compose_self_fallback` already appends a `Cancel site: Step 1d.7 outline gate` bullet AFTER the markers (lines 386-388). The new HTML comment is inserted BEFORE that bullet (immediately after `<!-- larch:run-summary v=1 -->`); the existing cancel-site bullet sits after both markers and its layout is unchanged.
- **Implement-side stage discrimination**: only Stage 3 (`compose_self_fallback`) carries the marker; Stage 1 (`run_body_render`) and Stage 2 (`run_body_render` with `--cost-unavailable`) both produce a real render-run-summary body and must remain unmarked. The harness explicitly regression-guards Stage 2 absence via `assert_not_contains`.
- **First-non-empty-line audit anchor**: `scripts/verify-run-log-completeness.sh:130` runs `final_summary_heading_bail_signal` which reads `final-summary.md`, finds the first non-empty stripped line, and matches `RUN_LOG_TERMINAL_OUTCOME_SUFFIX_EGREP` (= `(bailed(-needs-user-input)?|stalled|design-only|forked-dry-run|pr-created(-draft)?)$`). The fix places the banner AFTER the heading, so the heading remains first non-empty line. The strict placement assertion in each harness directly guards this.
- **Concurrent `<!-- larch:run-summary v=1 -->` consumers**: `scripts/ship-pr.sh`, `scripts/refresh-run-logs.sh`, and the implement summary-comment-template anchor on the existing marker. The new `<!-- larch:final-summary-fallback v1 -->` marker is purely additive and placed AFTER the existing marker; existing parsers see the existing marker unchanged.
- **Artifact-name surface**: design tmpdirs use `execution-issues.md` while committed implement run logs use `execution-issues.ndjson` (the actual file written when the run log is published). The banner text uses the artifact-neutral phrase "warning recorded in execution issues" so the same banner reads correctly in both contexts.

## Failure modes (top 3)

1. **Banner accidentally placed before the heading**: would break `final_summary_heading_bail_signal` audit parser, causing false-negative bail signals on every fallback run, polluting subsequent audit-runs reports. **Earliest warning**: the strict placement assertion in each harness (`first non-empty line starts with '## ... run '`, `second non-empty line starts with '**⚠ Degraded fallback'`) fires immediately in the regression test. **Mitigation**: harness assertion is the in-PR catch.

2. **HTML marker collides with existing `<!-- larch:run-summary v=1 -->` grep heuristics in ship-pr.sh / refresh-run-logs.sh**: theoretically, an overly broad grep like `grep '<!-- larch:'` would now match both markers. **Earliest warning**: ship-pr.sh or refresh-run-logs.sh dry-run on a fixture that includes a fallback-marked file. **Mitigation**: the new marker uses the distinct prefix `final-summary-fallback`, so any grep targeting the exact existing `run-summary v=1` marker continues to match only the existing one; broader greps were already brittle and are not pinned by this fix.

3. **Implement-side Stage-2 `--cost-unavailable` body is accidentally marked**: the implement-side has 3 stages and only Stage 3 should be marked. If a future refactor moves the marker into a shared helper or `run_body_render` itself, Stage 2 (which produces a full render) would be falsely marked degraded. **Earliest warning**: the harness `assert_not_contains` on `fallback_stage1` (`stage1 must not carry degraded-fallback marker`) catches this. **Mitigation**: keep the marker insertion inline in the local `compose_self_fallback` function body, not in any shared helper; the harness regression guard pins this invariant.

## Testing strategy

- `bash skills/design/scripts/test-render-final-summary.sh` — existing harness with the renderer-fail block extended by the new fallback-marker + placement + run-summary-marker assertions.
- `bash skills/implement/scripts/test-write-final-report.sh` — existing harness with the `renderer fallback stage2` block extended by the new banner/marker/placement assertions plus the `assert_not_contains` on stage1 absence.
- `make lint` (or `bash scripts/relevant-checks.sh`) — repo-wide pre-commit / linter sweep. This catches Bash 3.2 portability issues, sibling-.md presence, and skill-structure regressions.
- Manual smoke verification: the existing `scripts/test-render-final-summary-bash32.sh` (Bash 3.2 portability harness) must still pass after the changes; the new `printf` lines use plain literal markdown and pose no Bash 3.2 concern.

No new test scripts are created; new assertions attach to existing renderer-failure / Stage-2 fallback blocks in both harnesses, eliminating duplicate failure setup and matching the SIMPLE-tier "prefer single-file edits" bias.


## Acceptance

- `bash skills/design/scripts/test-render-final-summary.sh` exits 0; new assertions for the fallback banner, `<!-- larch:final-summary-fallback v1 -->` marker, existing `<!-- larch:run-summary v=1 -->` marker, and strict heading-then-banner placement all pass inside the existing renderer-fail block.
- `bash skills/implement/scripts/test-write-final-report.sh` exits 0; new assertions for the fallback banner, fallback HTML marker, and strict heading-then-banner placement pass inside the existing `renderer fallback stage2` block; `assert_not_contains` for the marker/banner in `fallback_stage1` also passes.
- `bash scripts/test-render-final-summary-bash32.sh` continues to pass (no Bash 3.2 regression from the new printf lines).
- `bash scripts/relevant-checks.sh` (`make lint`) exits 0; in particular, sibling-.md (`render-final-summary.md`, `write-final-report.md`) updates are present and skill-structure linter accepts the changes.
- Inspect a generated fallback `final-summary.md` (from either harness) and visually confirm: the first non-empty line is the `## ... run <RUN_ID> — <OUTCOME>` heading, the second non-empty line is `**⚠ Degraded fallback — full renderer failed; warning recorded in execution issues.**`, the existing `<!-- larch:run-summary v=1 -->` marker is present, the new `<!-- larch:final-summary-fallback v1 -->` marker appears directly after it, and the script exited 0.
- Neither `compose_self_fallback` invocation changes script exit code; callers in SKILL.md (Step 0b, 5c items 8/10, Final-summary-block fences) continue to operate without modification.

diff_lines: 90
