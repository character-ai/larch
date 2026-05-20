## Goal
Standardize end-of-run summary: shared renderer + per-skill wrappers

## Implementation Plan
# Implementation Plan: Standardize end-of-run summary in /implement and /fix-issue

## Files to modify/create

### New files
- `scripts/render-run-summary.sh` — **shared** markdown bullet-block renderer called by both write-final-report scripts; normalizes common fields (outcome, mode, path, duration, tokens, cost, issue, PR, reviews, OOS, exec-issues, warnings, run-logs) from CLI args and env vars; keeps the two callers byte-identically aligned; renders Note: lines from an optional `--note-lines-file`
- `scripts/render-run-summary.md` — sibling contract
- `scripts/token-cost.sh` — per-vendor cost formatter (used internally by render-run-summary.sh; exported as standalone helper for test reuse)
- `scripts/token-cost.md` — sibling contract
- `skills/fix-issue/scripts/write-final-report.sh` — thin state-reader + note-builder for /fix-issue; reads `$FIX_ISSUE_TMPDIR/final-report-state.sh` and token data, normalizes fields, builds note lines, delegates rendering to `render-run-summary.sh`
- `skills/fix-issue/scripts/write-final-report.md` — sibling contract
- `skills/fix-issue/scripts/test-write-final-report.sh` — test harness for fix-issue final report
- `skills/fix-issue/scripts/test-write-final-report.md` — sibling stub for harness
- `scripts/test-render-run-summary.sh` — dedicated tests for the shared renderer (format, N/A semantics, sentinel tail)
- `scripts/test-render-run-summary.md` — sibling stub

### Modified files
- `skills/implement/scripts/write-final-report.sh` — extend with rich bullet block composer; add `--print-stdout` flag (mode-specific stdout contract: see Step 2)
- `skills/implement/scripts/write-final-report.md` — doc update: new schema, `--print-stdout` mode contract, outcome enum, per-vendor cost, `N/A` semantics
- `skills/implement/scripts/test-write-final-report.sh` — extend to cover all 8 implement outcomes + `--print-stdout` byte-identicality + N/A rendering + cost + Note lines + sentinel
- `skills/implement/references/summary-comment-template.md` — update `larch:final-summary` description to rich bullet block; note it is now the one marker that carries a data body; other three markers stay slim
- `skills/implement/SKILL.md` — Step 17: replace all conditional prose branches with single unconditional `write-final-report.sh --print-stdout` call; Step 18: update `write-final-report.sh` call to also use `--print-stdout`
- `skills/fix-issue/SKILL.md` — add `write-final-report.sh` calls at Step 3 not-material closure, Step 5a terminal-only (no GitHub post), Step 6b NON_PR after close+rename, Step 0 exit-1/exit-3 paths (terminal-only); skip exit-2 per FINDING_12
- `docs/configuration-and-permissions.md` — document `LARCH_CLAUDE_RATE_PER_M`, `LARCH_CODEX_RATE_PER_M`, `LARCH_CURSOR_RATE_PER_M`, and fallback semantics
- `docs/run-logs.md` — update final-summary.md section to describe new rich block vs unchanged upsert marker
- `scripts/refresh-run-logs.sh` — update PR_URL gating logic to reflect partial-data tolerance
- `scripts/refresh-run-logs.md` — update documentation per Edit-in-sync requirement
- `scripts/test-refresh-run-logs.sh` — update tests to cover partial-upsert behavior
- `Makefile` — add `test-fix-issue-write-final-report` target

## Approach

### Step 1: scripts/token-cost.sh + scripts/render-run-summary.sh (shared renderer)

Create a small stateless helper for per-vendor cost computation. Interface:

```bash
bash scripts/token-cost.sh \
  --claude-tokens <N> \
  --codex-tokens <N> \
  --cursor-tokens <N>
```

Output (stdout KV):
```
CLAUDE_COST=0.32 | N/A
CODEX_COST=0.10 | N/A
CURSOR_COST=0.03 | N/A
TOTAL_COST=0.45 | N/A
CLAUDE_TOKENS=<N>
CODEX_TOKENS=<N>
CURSOR_TOKENS=<N>
TOTAL_TOKENS=<N>
```

Cost computation: `cost_v = tokens_v / 1_000_000 * RATE_v`, two decimal places via `awk printf "%.2f"`. Rate lookup:
- Claude: `LARCH_CLAUDE_RATE_PER_M` → fallback `LARCH_TOKEN_RATE_PER_M` → N/A if unset/empty/zero
- Codex: `LARCH_CODEX_RATE_PER_M` → N/A if unset/empty/zero
- Cursor: `LARCH_CURSOR_RATE_PER_M` → N/A if unset/empty/zero

TOTAL sums only vendors with a numeric cost (N/A vendors excluded). If all vendors are N/A, TOTAL_COST=N/A.

Note: `token-cost.sh` is intentionally implement/fix-issue only. `/research` uses `token-tally.sh` which has different semantics (single-rate column). This divergence is documented in `token-cost.md` to prevent confusion (accepted OOS_5 finding).


### Step 1b: scripts/render-run-summary.sh interface

The shared renderer accepts normalized field arguments and writes the bullet block to a temp file, then optionally prints to stdout and/or posts via `tracking-issue-summary.sh`:

```bash
bash scripts/render-run-summary.sh \
  --skill <implement|fix-issue> \
  --outcome <value> \
  --run-id <id> \
  --mode <flags> \
  --workflow-path <SIMPLE|HARD|N/A> \
  --duration <elapsed> \
  --claude-tokens <n> --codex-tokens <n> --cursor-tokens <n> \
  --issue-number <n> --issue-url <url> \
  --pr-number <n> --pr-url <url> \
  --plan-review-accepted <n> --plan-review-total <n> --plan-review-mode <mode> \
  --code-review-accepted <n> --code-review-total <n> \
  --oos-count <n> --oos-urls <comma-list> \
  --exec-issues <n> --warnings <n> \
  --run-logs-path <path> \
  [--note-lines-file <file>] \
  [--print-stdout] \
  [--output-file <path>]
```

Outputs to `--output-file` (default: temp file), optionally prints to stdout via `--print-stdout`. KV envelope (`STATUS=ok`, `OUTPUT_FILE=<path>`) goes to stderr always (never stdout), preserving the byte-identical stdout contract.

Both `write-final-report.sh` scripts become thin state-readers: they read their respective state surfaces, compute per-vendor tokens, build a note-lines temp file, then exec `render-run-summary.sh` with normalized args. The upsert call (tracking-issue-summary.sh) remains in each caller since the marker and issue-number source differ between skills.

### Step 2: Extend skills/implement/scripts/write-final-report.sh (thin wrapper over render-run-summary.sh)

Replace the 3-line summary composer with the rich bullet block composer.

**`--print-stdout` mode contract (FINDING_1)**: In `--print-stdout` mode, stdout emits ONLY the markdown block (byte-identical to `summary-final.md`). The `COMMENT_URL`/`STATUS`/`ERROR` KV lines are sent to stderr when `--print-stdout` is active. In normal (non-print) mode, stdout remains KV-only (backward-compatible with `ship-pr.sh` callers). This mode split is documented in `write-final-report.md`. Tests assert that non-print stdout contains only KV lines, and print stdout contains only the markdown block.

**State reads (FINDING_2 - use actual persisted state keys)**:
- `parent-issue.md` → `ISSUE_NUMBER`, `RUN_ID`
- `session-env.sh` → `REPO`, `LARCH_TOKEN_SESSION_ID`, `LARCH_CLAUDE_SOURCE_FILE`
- `ship-pr-state.sh` → `PR_URL`, `PR_NUMBER`, `STALL_TRACKING`, `MERGE_RESULT`, `MERGE`, `DRAFT`, `FORKED_TARGET`, `PR_CLOSED`
- `finalize-state.sh` → `DESIGN_ONLY_DONE`, `DONE_RENAME_APPLIED`; read `BAIL_NEEDS_USER_INPUT`, `STALL_TRACKING` as fallback when ship-pr-state.sh absent
- Run flags not durably persisted today (`quick_mode`, `no_issues`): read from a new `$IMPLEMENT_TMPDIR/run-flags.sh` file (KV: `QUICK_MODE`, `NO_ISSUES`, `WORKFLOW_PATH`) written by `/implement` at Step 1 post-design-boundary using the sanctioned `scripts/persist-post-plan-keys.sh` or a new thin writer; render `N/A` when the file is absent (backward compatibility)
- `larch-logs/implement/<RUN_ID>/token-report.json` — prefer this cached path; fall back to `$IMPLEMENT_TMPDIR/token-report-rendered.json`; fall back to on-demand `token-report.sh --full --format json`
- `larch-logs/implement/<RUN_ID>/timing-report.json` → total elapsed
- `larch-logs/implement/<RUN_ID>/plan-review-tally.json` → `accepted_count`, `rejected_count`, `mode`
- `larch-logs/implement/<RUN_ID>/code-review-tally.json` → `accepted_count`, `rejected_count`
- `larch-logs/implement/<RUN_ID>/oos-issues.ndjson` → count and URLs
- `larch-logs/implement/<RUN_ID>/execution-issues.ndjson` → tool-failures + warnings counts

**Outcome resolution (FINDING_5 — use actual MERGE_RESULT key)**:
Priority order:
1. `STALL_TRACKING=true` → `stalled`
2. `FORKED_TARGET=true` (from ship-pr-state.sh) → `forked-dry-run`
3. `DESIGN_ONLY_DONE=true` (from finalize-state.sh) → `design-only`
4. `MERGE_RESULT=merged` OR `MERGE_RESULT=admin_merged` → `merged`
5. `MERGE_RESULT=already_merged` → `force-merged-externally`
6. `PR_NUMBER` set AND `DRAFT=true` → `pr-created-draft`
7. `PR_NUMBER` set AND `DRAFT=false` AND `MERGE=false` → `pr-created`
8. fallback → `bailed`

**Block format** (byte-identical terminal/GitHub, upsert marker unchanged):
```markdown
## /implement run <RUN_ID> — <outcome>

- **Outcome**: <outcome>
- **Mode**: `<flags>` | N/A
- **Path**: SIMPLE|HARD|N/A
- **Duration**: <elapsed>
- **Tokens**: <total>k total — Claude <n>k, Codex <n>k, Cursor <n>k
- **Cost**: TOTAL ~$X.XX — Claude $X.XX, Codex $X.XX, Cursor $X.XX
- **Issue**: #<N> — <https://...>
- **PR**: #<N> — <https://...> | N/A
- **Plan review**: <N>/<total> accepted | skipped (quick mode) | N/A
- **Code review**: <N>/<total> accepted | N/A
- **OOS filed**: <N> — #NNN, #NNN | 0
- **Exec issues**: <N>
- **Warnings**: <N>
- **Run logs**: `larch-logs/implement/<RUN_ID>/`

<!-- larch:run-summary v=1 -->
```

Note: upsert marker stays `<!-- larch:final-summary v1 runid=$RUN_ID -->` — unchanged. The `<!-- larch:run-summary v=1 -->` sentinel is only inside the body content (FINDING_11).

**Mode-specific Note: lines** (emitted to same file and stdout, after the block, for byte-identical terminal+GitHub):
- `FORKED_TARGET=true`: 5-bullet fork CI dry-run notes (moved from Step 17 prose); emitted when outcome=forked-dry-run
- `DESIGN_ONLY_DONE=true AND NO_ISSUES=true`: design-only no-issues reminder
- `DESIGN_ONLY_DONE=true`: design-only reminder
- `DRAFT=true`: draft reminder
- `MERGE=false AND DRAFT=false AND PR_NUMBER set`: non-merge reminder

**Also migrate OOS skip appendix and UPSTREAM_DESIGN_ISSUE fork addendum** from Step 17 prose to the script. These were identified by pragmatic reviewers as missing from the plan's Note lines list.

Existing `--comment-only` mode preserved. Both output paths (summary-final.md and larch-logs/.../final-summary.md) write the same body including Note lines.

### Step 3: Update skills/implement/SKILL.md Steps 17 and 18

**Step 17** (FINDING_4): Remove ALL conditional pre-guards (DESIGN_ONLY_DONE, quick_mode, forked_target). Replace with single unconditional call:
```bash
${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/write-final-report.sh \
  --implement-tmpdir "$IMPLEMENT_TMPDIR" --print-stdout
```
The script handles all outcomes internally. Remove: fork CI dry-run report prose, design-only/quick_mode/draft/merge note prose. Keep: token summary block (unchanged, follows the script call).

**Step 18**: Change existing `write-final-report.sh` call to also add `--print-stdout` and remove `forked_target=false AND repo_unavailable=false` gate. The script's own upsert logic is gated on having a valid ISSUE_NUMBER and non-repo-unavailable state internally. The Step 18 `|| true` best-effort wrapper and failure logging via `append-tool-failure.sh` are preserved.

Also add `run-flags.sh` persistence call at Step 1 post-plan boundary (after `post-design-boundary.sh` runs) to write `QUICK_MODE`, `NO_ISSUES`, `WORKFLOW_PATH` from session state to `$IMPLEMENT_TMPDIR/run-flags.sh`.

### Step 4: New skills/fix-issue/scripts/write-final-report.sh

**State from `$FIX_ISSUE_TMPDIR/final-report-state.sh`** (new KV file — FINDING_8):
```bash
ISSUE_NUMBER=<N>
CLASSIFICATION=PR|NON_PR|NOT_MATERIAL
PR_NUMBER=<N>  # optional
PR_URL=<url>   # optional
OUTCOME=<value>  # one of the 8 enum values
```
Written at the point each value is known (see Step 6).

For no-tmpdir paths: accept `--issue-number`, `--outcome`, `--duration`, `--tokens`, `--cost` as CLI args.

**Outcome enum** (hyphen-normalized, FINDING_9):
- `pr-merged`, `pr-open`, `closed-non-pr`, `closed-not-material`
- `bailed-implement-failed`, `bailed-adopted-issue-closed`
- `no-candidate`, `lock-failed`

Note: `prelock-error` (exit-2) is excluded per FINDING_12 — exit-2 emits plain text only, no write-final-report call.

**GitHub post** (FINDING_3): Use `tracking-issue-summary.sh upsert-summary` with `<!-- larch:fix-issue:final-summary v=1 -->` marker for idempotency and redaction. Skip GitHub post on `pr-merged`/`pr-open` outcomes (implement covers it). Skip on `no-candidate`/`lock-failed` (no issue to post to).

**`--print-stdout` mode**: same as /implement version — markdown block only to stdout, KV to stderr. For no-tmpdir paths this means stdout is the block, KV sent to stderr.

### Step 5: scripts/refresh-run-logs.sh updates (FINDING_10)

Remove `PR_URL` hard gate for `write-final-report.sh`. The script itself checks for PR_URL in state and renders N/A when absent. Update `refresh-run-logs.md` documentation and `test-refresh-run-logs.sh` to cover partial-data (early upsert) behavior. This is required per the Edit-in-sync note at `refresh-run-logs.md:77-80`.

### Step 6: Update skills/fix-issue/SKILL.md

**Write final-report-state.sh at each call site** (FINDING_8):
- After Step 4 classification: write `ISSUE_NUMBER` and `CLASSIFICATION` to `$FIX_ISSUE_TMPDIR/final-report-state.sh`
- After Step 5a PR capture (success): append `PR_NUMBER`, `PR_URL`, `OUTCOME=pr-merged` (or `pr-open`) to state
- After Step 5a bail: write `OUTCOME=bailed-implement-failed` (or `bailed-adopted-issue-closed`)
- After Step 3 not-material: write `OUTCOME=closed-not-material` and call `write-final-report.sh --print-stdout`
- After Step 6b NON_PR close+rename (FINDING_6): write `OUTCOME=closed-non-pr` and call `write-final-report.sh --print-stdout`

**Call sites with `--print-stdout`**:
- Step 3 not-material: after `tracking-issue-write.sh rename`, before Step 8
- Step 5a bail paths: both bailed cases, terminal-only (skip GitHub post on PR paths)
- Step 6b after close+rename: NON_PR and not-material paths (FINDING_6 — not Step 5b)
- Step 0 exit-1 (no-candidate): `write-final-report.sh --outcome no-candidate --print-stdout` (terminal-only)
- Step 0 exit-3 (lock-failed): `write-final-report.sh --outcome lock-failed --print-stdout` (terminal-only)
- Step 0 exit-2: plain text error only, do NOT call write-final-report.sh (FINDING_12)

**Step 5a PR delegation**: no fix-issue write-final-report.sh call — /implement owns the tracking-issue summary. The Step 5a success path note (terminal-only `--print-stdout`) should appear after the Step 6 breadcrumb and Step 6a/6c handling, not between the /implement return and the Step 6 breadcrumb (per the Step 5a anti-halt directive).

### Step 7: Test harnesses

**skills/implement/scripts/test-write-final-report.sh** additions:
- All 8 outcome values in the outcome enum via fixture tmpdirs
- `--print-stdout` mode: assert stdout === markdown file (no KV lines in stdout)
- Normal mode: assert stdout contains only KV lines (COMMENT_URL/STATUS/ERROR)
- N/A rendering: parametric fixture — zero out each source file, verify graceful N/A
- Per-vendor cost with 0/1/2/3 rate envs set
- Schema sentinel `<!-- larch:run-summary v=1 -->` present
- Mode-specific Note lines for each: `--draft`, `--merge=false`, `--design-only`, `--design-only --no-issues`, `forked_target=true`
- `STALL_TRACKING=true` outcome via `ship-pr-state.sh` fixture (not via `.git/larch-stalled-run.txt`)
- forked+quick combination correctly handled
- MERGE_RESULT key mapping: `merged`, `admin_merged`, `already_merged`

**skills/fix-issue/scripts/test-write-final-report.sh** (new):
- All 8 fix-issue outcome values (hyphen-normalized)
- PR-path skip (no GitHub post assertion via mocked upsert)
- `no-candidate`/`lock-failed` no-tmpdir paths via CLI flags
- Byte-identicality for non-PR paths
- N/A fields rendering
- upsert-summary called with correct fix-issue marker

**scripts/test-refresh-run-logs.sh**: add coverage for partial-upsert (early call without PR_URL).

**scripts/test-implement-structure.sh**: assert Step 17 no longer contains branched-prose substrings (`Fork CI Dry-Run Complete`, `--draft was set`, `--merge was not set`, `--design-only was set`) and contains single `write-final-report.sh --print-stdout` invocation.

**Makefile**: add two new targets:
```
test-fix-issue-write-final-report:
	bash scripts/harness-timer.sh $@ bash skills/fix-issue/scripts/test-write-final-report.sh
test-render-run-summary:
	bash scripts/harness-timer.sh $@ bash scripts/test-render-run-summary.sh
```
Wire both into `test-harnesses-7` alongside existing `test-write-final-report`. Add to `.PHONY` list. The `test-render-run-summary` target covers shared renderer format, N/A semantics, and sentinel tail separately from the per-caller wrappers.

### Step 8: Documentation updates

- `docs/configuration-and-permissions.md`: Add `LARCH_CLAUDE_RATE_PER_M`, `LARCH_CODEX_RATE_PER_M`, `LARCH_CURSOR_RATE_PER_M` alongside existing `LARCH_TOKEN_RATE_PER_M`; document fallback semantics and N/A rendering
- `skills/implement/references/summary-comment-template.md`: Update `larch:final-summary` description to rich bullet block; note it is now the only marker carrying a data body (exception to the "slim pointer" rule); other three markers stay slim
- `docs/run-logs.md`: Update `final-summary.md` description to reflect new rich block content vs unchanged `larch:final-summary` upsert marker

## Edge cases

- **All fields N/A before state files exist**: every field defaults to N/A when source file/field absent. Script never exits non-zero on absent optional files.
- **No tmpdir on fix-issue exit paths**: `no-candidate`/`lock-failed` use CLI args for small known data set.
- **Early upsert refreshes**: `ship-pr.sh` and `refresh-run-logs.sh` calls show partial block with N/A. Acceptable per refresh tolerance.
- **`ship-pr.sh --comment-only` path**: unchanged — writes `summary-final.md` with best-available data, skips `final-summary.md`. The `--print-stdout` flag is NOT passed from `ship-pr.sh`.
- **Byte-identicality**: achieved by composing to tempfile, copying to output paths, then printing tempfile when `--print-stdout`. Single source of truth — no in-place difference between file and stdout content.
- **Token report read order**: prefer `larch-logs/.../token-report.json` (committed), then `$IMPLEMENT_TMPDIR/token-report-rendered.json` (rendered at Step 18), then on-demand `token-report.sh --full --format json`. Step 7a is NOT a caller per FINDING_7 — do not add it.
- **Early Step 17 invoke with partial data**: STALL_TRACKING not yet set because ship-pr-state.sh absent → outcome defaults to `bailed`. Partial N/A fields rendered. Acceptable.
- **DESIGN_ONLY runs**: design-only outcome handled by the script, Step 17 unconditional call produces correct design-only block.
- **fix-issue Step 0 exit-2**: plain text error only. No write-final-report.sh call. No final-report-state.sh write. The 8-value enum does not include prelock-error.

## Failure modes

1. **write-final-report.sh crash on bail path**: all reads wrapped in best-effort `|| true`. `set -euo pipefail` is present in the current script but exit-path hardening is needed — wrap the main composition function in a subshell that catches failures and emits a minimal fallback block (outcome + timestamp + N/A fields). The script must never exit non-zero when called from `|| true` bail paths in SKILL.md orchestration.

2. **Byte-identicality drift**: composed to tempfile first → stdout only gets a `cat` of the same tempfile. Mode-specific stdout (KV vs markdown) enforced by script-internal flag check.

3. **awk floating point**: use `printf "%.2f"` via awk for consistent two-decimal rendering. `awk 'BEGIN{printf "%.2f\n", n}'` is portable.

4. **final-report-state.sh missing fields on fix-issue path**: script reads with `|| true` defaults; renders N/A for each absent field. Post still happens with partial data rather than silently skipping.

## Testing strategy

- Extend `skills/implement/scripts/test-write-final-report.sh` with fixture-tmpdir approach per outcome
- New `skills/fix-issue/scripts/test-write-final-report.sh` mirroring implement harness
- Extend `scripts/test-implement-structure.sh` to assert branched prose is gone from Step 17/18
- Extend `scripts/test-refresh-run-logs.sh` for partial-upsert coverage
- All new tests wired into Makefile and run as part of `make lint`

diff_lines: 560

## Test plan
(no test plan section in plan-file)
