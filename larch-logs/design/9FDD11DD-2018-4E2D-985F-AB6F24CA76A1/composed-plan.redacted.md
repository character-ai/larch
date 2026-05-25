## Plan

# Implementation Plan: Switch to coder=codex default in /implement and fixer

## Background

Issue #2756 asks us to switch the default coder back to `codex` in two places:
1. `/implement` Step 2 dispatcher: the omitted-`--coder` default value.
2. The "fixer" — the review-fix dispatch in `review-and-fix.sh` and the lint-fix dispatch in `lint-fix-loop.sh`.

This reverses two prior PRs:
- **#2400** (commit 54f0a262, May 19): switched `/implement` dispatcher default from `codex` → `cursor` and updated the `### Implementer waterfall` prose to `Cursor → Codex → Claude`.
- **#2452** (commit 4d808eb6, May 20): reordered `run_coder_dispatch()` in `review-and-fix.sh` and the primary branch in `lint-fix-loop.sh` to try Cursor before Codex.

After this change:
- `/implement` Step 2 dispatcher default reverts to `codex` (back to pre-#2400 behavior).
- `### Implementer waterfall` in `skills/implement/SKILL.md` reverts to `Codex → Cursor → Claude`.
- `review-and-fix.sh` `run_coder_dispatch()` tries codex first, falls back to cursor.
- `lint-fix-loop.sh` tries codex first, falls back to cursor.
- All sibling `.md` docs, test assertions, SECURITY.md, and `docs/linting.md` cross-references updated to match.

## Approach

This is a mechanical revert of two well-localized default-flip changes. The change set falls into three groups: (A) production-script value flips, (B) test-assertion flips, and (C) cross-doc prose flips. The substantive logic doesn't change — only the order of attempts and the omitted-flag default value.

Two distinctions preserved (do **not** flip):
- `SECURITY.md` line 66 — `aggregate-findings.sh` outer aggregator waterfall ordering is `Cursor → Codex → Claude`. This is independent of the implementer waterfall; **leave alone**.
- `docs/collaborative-sketches.md` line 52 — `/design` plan-review per-archetype fallback chain. Independent of the implementer waterfall; **leave alone**.

## Files to modify/create

### UPDATED: `skills/implement/scripts/step2-implement.sh`

Lines 121-124:
- Update comment from `# Default coder is cursor (Cursor spawn path) when --coder is omitted.` to `# Default coder is codex (Codex spawn path) when --coder is omitted.`
- Change `CODER="cursor"` to `CODER="codex"`.

No other logic changes — the cursor-present gate at lines 184-193 still applies when `--coder=cursor` is passed explicitly. Codex has no equivalent presence gate at the dispatcher level; an `--coder=codex` invocation from a non-git cwd exits 2 at the `git rev-parse --show-toplevel` check (lines 210-214), which is the desired fail-closed behavior.

### UPDATED: `skills/implement/scripts/step2-implement.md`

Sibling contract for `step2-implement.sh`. Update any prose mentioning the default coder being `cursor` to `codex`. Verify the file currently mentions the cursor-first default and replace with codex-first.

### UPDATED: `skills/review-and-fix/scripts/review-and-fix.sh`

In `run_coder_dispatch()` (lines 248-279):
- Swap the codex and cursor blocks so codex is attempted first, with cursor as the fallback.
- Preserve the `cursor_launcher_load_model_args && cursor_launcher_setup_auth_argv` precondition gating for the cursor branch (don't merge it into a non-gated retry — without auth/model setup, the cursor block must be skipped).
- The post-dispatch breadcrumb `"⚠ review-and-fix: coder dispatch failed (both codex and cursor)"` stays unchanged (it lists both tools symmetrically).

Approximate result:
```
if codex succeeds → return 0 with tool=codex
elif cursor_launcher_load_model_args && cursor_launcher_setup_auth_argv && cursor succeeds → return 0 with tool=cursor
else emit breadcrumb and return 1
```

### UPDATED: `skills/review-and-fix/scripts/review-and-fix.md`

Sibling contract. Update any prose mentioning the dispatch order from "Cursor → Codex" to "Codex → Cursor", consistent with the script change.

### UPDATED: `scripts/lint-fix-loop.sh`

Lines 258-263: swap the order of the `if/elif` branches so codex is tried first when `CODEX_PRESENT=true`, with cursor as the fallback when `CURSOR_PRESENT=true`. Keep the `run_codex()` and `run_cursor()` function definitions (lines 155-178) unchanged.

### UPDATED: `scripts/lint-fix-loop.md`

Sibling contract. Update prose to reflect codex-first lint-fix dispatch.

### UPDATED: `skills/implement/scripts/test-step2-dispatch.sh`

Test 1b (lines 98-151): revert to the pre-#2400 shape — a non-git cwd assertion. New Test 1b:
- Comment: "Test 1b: default coder (neither flag set) is codex. From a non-git cwd the codex path fails the git-tree precondition and exits 2 — if the default were still claude, the dispatcher would early-return STATUS=claude_fallback from the git-free claude branch with exit 0."
- Remove the cursor stub binary + PATH manipulation + manifest stub block.
- Run dispatcher from a temp non-git directory with `--tmpdir`, `--plan-file`, `--feature-file` only (no `--cursor-present`).
- Assert exit=2 and stderr contains `"must be invoked from within a git working tree"`.
- Fail message: `"default coder should be codex (non-git cwd → git-tree exit 2), got exit=$EXIT err=$ERR"`.

Other tests (1c, 3, 3b, 3b2, etc.) reference Test 1b in their comments — those references stay accurate after the flip (Test 1b still tests omitted-`--coder` default behavior, just expecting codex instead of cursor).

### UPDATED: `skills/implement/scripts/test-step2-dispatch.md`

Line 5: replace "Default coder (no flag) is cursor — verified via non-git cwd with no `--cursor-present`: dispatcher exits 0 with `STATUS=claude_fallback` (cursor presence check fires before git-tree lookup; codex default would exit 2 instead)." with: "Default coder (no flag) is codex — verified via non-git cwd: dispatcher exits 2 with `must be invoked from within a git working tree` because the codex path runs `git rev-parse --show-toplevel` (cursor default would exit 0 with `STATUS=claude_fallback` instead via the cursor-present gate)."

### UPDATED: `scripts/test-implement-step2-routing.sh`

Line 32: `assert_contains "$IMPLEMENT_SKILL" 'Codex → Cursor → Claude' "implement waterfall"`.

Line 38: `assert_not_contains "$IMPLEMENT_SKILL" "When \`coder_explicit=true\`, the explicit value wins. Do not apply the Codex → Cursor → Claude waterfall" "removed blanket explicit-coder bypass sentence"`.

### UPDATED: `scripts/test-implement-step2-routing.md`

Line 7: replace `waterfall order (Cursor → Codex → Claude)` with `waterfall order (Codex → Cursor → Claude)`.

### UPDATED: `skills/implement/SKILL.md`

Section `### Implementer waterfall`:

Line 848: "default availability waterfall prefers **Cursor → Codex → Claude** (Cursor when its probes pass; otherwise Codex when available; otherwise Claude main agent — bullets below)." → "default availability waterfall prefers **Codex → Cursor → Claude** (Codex when its probes pass; otherwise Cursor when available; otherwise Claude main agent — bullets below)."

Line 850: "If `cursor_available=true`, set `coder=cursor`. This is the default implementer when `--coder` is omitted." → "If `codex_available=true`, set `coder=codex`. This is the default implementer when `--coder` is omitted."

Line 851: "If `cursor_available=false` AND `codex_available=true`, set `coder=codex` and `coder_fallback_target=codex`, print `**⚠ Cursor unavailable — falling back to Codex implementer.**`, and append `Step 0 — Cursor unavailable: waterfall fallback to codex` to the `Warnings` section of `$IMPLEMENT_TMPDIR/execution-issues.md`. Do NOT set `coder_fallback=true` on this path; Codex is an external implementer, not a degraded fallback." → "If `codex_available=false` AND `cursor_available=true`, set `coder=cursor` and `coder_fallback_target=cursor`, print `**⚠ Codex unavailable — falling back to Cursor implementer.**`, and append `Step 0 — Codex unavailable: waterfall fallback to cursor` to the `Warnings` section of `$IMPLEMENT_TMPDIR/execution-issues.md`. Do NOT set `coder_fallback=true` on this path; Cursor is an external implementer, not a degraded fallback."

Line 852: "If `cursor_available=false` AND `codex_available=false`, set `coder=claude` …" → "If `codex_available=false` AND `cursor_available=false`, set `coder=claude` …" (note: the `**⚠ /implement Step 2: Cursor and Codex both unavailable …**` warning text and the `Step 0 — Cursor and Codex unavailable: waterfall fallback to claude` execution-issues line list both tools — those can stay in their current alphabetical/legacy ordering or be flipped for cosmetic consistency; preserving the existing wording is acceptable since the test only checks for the literal substring `Cursor and Codex both unavailable`, see `test-implement-step2-routing.sh` line 40).

### UPDATED: `SECURITY.md`

Line 40 (within the long `**External tool delegation**` paragraph): one substring `routes by external availability: Cursor → Codex → Claude (main agent only when both are unavailable)` → `routes by external availability: Codex → Cursor → Claude (main agent only when both are unavailable)`. The same paragraph contains the sentence "Operators who want a stricter sandbox model should prefer `--coder=codex`." — since codex becomes the default after this change, this sentence becomes redundant but is still factually correct; leave it (mechanical surgical-changes preference).

Line 52: "follows Cursor → Codex → Claude by external availability. … This can select Codex without an explicit `--coder=codex` when Cursor is unavailable" → "follows Codex → Cursor → Claude by external availability. … This can select Cursor without an explicit `--coder=cursor` when Codex is unavailable".

**Do not modify** line 66 (`aggregate-findings.sh` outer aggregator waterfall, `Cursor → Codex → Claude`) — that is a separate dispatch chain and out of scope.

### UPDATED: `docs/linting.md`

Line 251: replace `omitted-`--coder` Cursor → Codex → Claude waterfall` with `omitted-`--coder` Codex → Cursor → Claude waterfall`.

### UPDATED: `CHANGELOG.md`

Add a new top-of-file entry (matching repo style — short paragraph with file list and issue closure tag) describing the revert: default coder flip back to `codex` in `/implement` Step 2 dispatcher and `### Implementer waterfall`, dispatch order flip back to `codex` first in `review-and-fix.sh` and `lint-fix-loop.sh`, harness/sibling-doc/cross-doc updates. Closes #2756.

## Edge cases

1. **Non-git cwd with omitted `--coder`**: dispatcher now defaults to codex, so it exits 2 at the git-tree precondition rather than the previous cursor-present gate. Test 1b pins this (covered in test changes above). Operators currently relying on the cursor-present gate's `claude_fallback` early-return from a non-git cwd should pass `--coder=claude` or `--coder=cursor` explicitly going forward.

2. **`--coder=cursor` from non-git cwd**: unchanged — the cursor-present gate (lines 184-193) still fires first and emits `STATUS=claude_fallback`. Tests 3b/3b2 already cover this.

3. **`--coder=claude`**: unchanged — early return at lines 168-172 before any default-coder logic.

4. **`/implement` SKILL.md Step 0 waterfall when only one external is available**:
   - codex available + cursor unavailable → coder=codex (was: coder=codex via secondary fallback; now: coder=codex via primary path; manifest doesn't change since neither path sets `coder_fallback=true`).
   - cursor available + codex unavailable → coder=cursor (was: coder=cursor via primary path; now: coder=cursor via secondary fallback with new "Codex unavailable" warning; manifest doesn't set `coder_fallback=true`).
   The change in *which* tool is the "primary" affects only the warning prose and the secondary-fallback's name; the resulting `coder` value is correct in both cases. The `coder_fallback=true` flag is only set in the both-unavailable claude path, which is unaffected.

5. **`review-and-fix.sh` when cursor auth/model setup fails but codex is up**: before flip, this hit the codex fallback after cursor auth check failed. After flip, codex is tried first regardless of cursor auth state — net effect: same behavior when both tools are healthy (codex now wins by being first). When codex is down and cursor auth fails, behavior identical to before (both fail, breadcrumb emitted, return 1).

6. **`lint-fix-loop.sh` with `CODEX_PRESENT=false` and `CURSOR_PRESENT=true`**: before flip, cursor primary, codex fallback. After flip, codex skipped (not present), cursor runs as secondary. Net behavior: cursor runs in both cases when codex is absent.

## Failure modes

Omitted — this is a mechanical revert of well-understood prior changes, no new architectural risk surface.

## Testing strategy

- `make test-implement-step2-routing` exercises `scripts/test-implement-step2-routing.sh` — must pass with the flipped waterfall assertion.
- `skills/implement/scripts/test-step2-dispatch.sh` — Test 1b updated to assert codex default via non-git-cwd path; all other tests in the file (1c, 3, 3b, 3b2, etc.) unchanged in behavior.
- `skills/review-and-fix/scripts/test-review-and-fix.sh` — verify whether existing assertions pin the dispatch order; if yes, update; if no, no test changes needed there.
- `make lint` (whole pre-commit hook suite) — runs `agent-lint`, S030 path pins, etc. The flips do not introduce new literal paths.
- Manual: `bash scripts/relevant-checks.sh` after every file change.

## Diff size estimate

Substantive code: ~3 lines in `step2-implement.sh`, ~25 lines net in `review-and-fix.sh` (block swap), ~6 lines net in `lint-fix-loop.sh` (block swap), ~25 lines net in `test-step2-dispatch.sh` (Test 1b restructure), ~3 lines in `test-implement-step2-routing.sh`. Prose: ~6 lines in `SKILL.md`, ~2 lines in `SECURITY.md`, ~1 line in `docs/linting.md`, ~5 lines in sibling .md docs combined, ~3 lines in CHANGELOG.


## Acceptance

- `skills/implement/scripts/step2-implement.sh`: omitted-`--coder` default value is `codex` (was `cursor`); comment at the default-assignment line reflects the new default.
- `skills/review-and-fix/scripts/review-and-fix.sh` `run_coder_dispatch()`: tries codex first, then cursor (auth/model gated).
- `scripts/lint-fix-loop.sh`: tries codex first when `CODEX_PRESENT=true`, then cursor when `CURSOR_PRESENT=true`.
- `skills/implement/SKILL.md` `### Implementer waterfall`: prose reads "Codex → Cursor → Claude" with `codex_available` as the primary branch and `cursor_available` as the secondary fallback.
- `skills/implement/scripts/test-step2-dispatch.sh` Test 1b: asserts default codex via non-git-cwd → exit 2 with `must be invoked from within a git working tree` (was: stub-cursor → STATUS=bailed).
- `scripts/test-implement-step2-routing.sh`: `assert_contains` pins "Codex → Cursor → Claude"; `assert_not_contains` regression text references the same flipped order.
- `SECURITY.md`: implementer waterfall references at lines 40 and 52 read "Codex → Cursor → Claude". Line 66 (aggregator waterfall) and docs/collaborative-sketches.md line 52 (plan-review chain) are NOT modified — they are independent dispatch chains.
- `docs/linting.md`: `test-implement-step2-routing` row references "Codex → Cursor → Claude".
- Sibling `.md` docs (`step2-implement.md`, `review-and-fix.md`, `lint-fix-loop.md`, `test-step2-dispatch.md`, `test-implement-step2-routing.md`) updated to match their script counterparts.
- `CHANGELOG.md`: new top-of-file entry describes the revert and closes #2756.
- `make test-implement-step2-routing` passes.
- `make lint` passes (pre-commit hook chain including agent-lint S030 path pins).
- `bash scripts/relevant-checks.sh` passes.

diff_lines: 90
