## Goal
Fix token cost reporting pipeline to deduplicate JSONL usage rows, add per-bucket rate computation, update stale rate constants, and standardize dollar-primary output format across /design, /implement, and /fix-issue.

## Implementation Plan
## Plan

**This is the FINAL implementation plan** — the issue body carries plan-quality detail (file paths with line numbers, concrete jq patches, exact per-bucket rate constants from official vendor pricing pages verified 2026-05-22, exact target output format strings, and 10 numbered acceptance criteria including bug-4 added in the May 23 augmentation). The bug-1 over-count was empirically verified against the live Claude transcript (230 usage rows vs 88 unique `(requestId, message.id)` tuples). No reviewer panel was run — this issue is admitted directly to `/implement` with the issue body's directives as the authoritative plan. Implementor should execute exactly the changes listed; intermediate sketches and contested-decision artifacts do not exist for this run.

### Goal

Fix the larch token cost reporting pipeline (`scripts/token-report.sh` + `scripts/token-cost.sh` + `scripts/render-cost-line.sh` + `scripts/render-run-summary.sh`) so:
1. Reported costs match actual API billing within ±10% across a recorded transcript fixture.
2. Both `/design` and `/implement` (and `/fix-issue`) terminal cost surfaces use a single dollar-primary format with per-vendor breakdown (`💰 Cost: TOTAL ~$X.XX — Claude $A, Codex $B, Cursor $C  |  Tokens: <T>k`).

Four compounding bugs are addressed in one PR (bug-1 may land separately as a small standalone first commit; bugs 2-4 land atomically):

1. **Bug 1 — JSONL duplicate-counting**: `token-report.sh` sums every `.message.usage.*` row in the transcript, but each Claude API response is recorded in 2-4 rows with identical `(requestId, message.id, cache_*_input_tokens, output_tokens)`. Verified on the May 22 #2382 transcript: 230 usage rows but 88 unique `(requestId, message.id)` tuples (2.6× over-count).
2. **Bug 2 — flat blended `$/M total tokens` rates**: `token-cost.sh` accepts only `--claude-tokens N` (aggregate) and multiplies by a single rate. cache_read is ~94% of token volume but priced 8-50× below other buckets; the blended rate overcharges cache_read and undercharges output.
3. **Bug 3 — stale default rate constants**: defaults reflect pre-Opus-4.5 pricing ($6/M Claude). Opus 4.7 is now $5 input / $0.50 cache_read / $6.25 cache_write_5m / $10 cache_write_1h / $25 output (per https://platform.claude.com/docs/en/about-claude/pricing verified 2026-05-22).
4. **Bug 4 — /implement final report format**: `render-run-summary.sh` produces TWO separate bullets (a tokens-primary `**Tokens**` line + a `**Cost**` line), and `token-report.sh --summary` produces a tokens-only chat line with NO dollars. Replace both with the dollar-primary single-line format from `/design`'s `render-cost-line.sh`.

### Files to create

1. **`scripts/test-token-report-dedup.sh`** (NEW) — pin the JSONL dedup invariant with a fixture jsonl carrying 5-10 deliberately-duplicated rows mapping to ~3 unique `(requestId, message.id)` tuples. Assert deduped counts match a hand-computed expected value.
2. **`scripts/test-token-cost-per-bucket.sh`** (NEW) — pin per-bucket rate arithmetic: `token-cost.sh --claude-input-tokens 100 --claude-cache-read-tokens 10000000 --claude-cache-write-5m-tokens 100000 --claude-output-tokens 5000` outputs `CLAUDE_COST=5.75` under default Opus 4.7 rates. Also cover per-bucket env var precedence, legacy blended env var fallback, malformed-env-var fallback.
3. **`scripts/test-render-cost-line-realism.sh`** (NEW) — end-to-end smoke test that replays a saved transcript fixture and asserts the rendered cost line's TOTAL is within ±10% of a hand-computed reference. Gate on `[ -f scripts/fixtures/token-cost-realism-2026-05.jsonl ]`.
4. **`scripts/test-render-cost-line-callsites.sh`** (NEW) — structure assertion that greps the repo for `render-cost-line.sh` invocations and fails if any call passes only the aggregate `--claude-tokens N` flag without the corresponding per-bucket flags.
5. **`scripts/test-render-run-summary-callsites.sh`** (NEW) — same idea for `render-run-summary.sh` invocations.
6. **`scripts/test-render-run-summary-format.sh`** (NEW) — pins the bug-4 format change: the rendered body MUST contain a single `- **Cost**: 💰 TOTAL ~$X.XX — Claude $A.AA, Codex $B.BB, Cursor $C.CC  |  Tokens: <T>k` line and MUST NOT contain a standalone `- **Tokens**:` bullet.
7. **`scripts/test-token-report-summary-format.sh`** (NEW) — pins bug-4 for the `--summary` mode: asserts the output line contains the substrings `Cost: TOTAL`, `Claude $`, `Codex $`, `Cursor $`, and `Tokens:`.
8. **`skills/report-tokens/scripts/test-report-tokens-recompute.sh`** (NEW) — regression test for `/larch:report-tokens` historical re-rendering. Uses a fixture run-log; asserts both legacy and recomputed cost columns are rendered.

### Files to modify — runtime

9. **`scripts/token-report.sh`** — fix Bug 1 (JSONL dedup) by changing the jq pipeline in `render_jq()` (around lines 150-190; search for the `usage_row()` definition and the `[.[] | select(.message.usage != null) | usage_row(.; $marks)]` array literal). Add `rid: .requestId` and `mid: .message.id` fields to `usage_row()`. After the array literal, pipe through `group_by((.rid // "") + "|" + (.mid // "")) | map(.[0])` (take-first-of-group, NOT sum) before any downstream aggregate. Critical invariant: duplicate rows have IDENTICAL `requestId`, IDENTICAL `message.id`, AND IDENTICAL usage values — `group_by + take-first` is correct; do NOT sum the duplicates and divide.

   Expose per-bucket counts. Emit a new `BUCKETS_*` block in `--format json` output: per-vendor `{input, cache_read, cache_create_5m, cache_create_1h, output, total}`. Add a CLI shape `token-report.sh --buckets --vendor <claude|codex|cursor>` that prints `INPUT=N CACHE_READ=N CACHE_WRITE_5M=N CACHE_WRITE_1H=N OUTPUT=N` for the requested vendor on stdout. Preserve the existing `unavailable` failure-mode contract (exit 0 with a single stderr line). Do NOT touch the `LARCH_DEBUG_TOKEN_REPORT` debug-knob behavior or its allowlist (`1|true|TRUE|True|yes|YES|Yes|on|ON|On`).

   **Bug-4 in `--summary` mode**: change the summary jq branch (around lines 382-391, search for `elif $mode == "summary" then`) to compute per-vendor dollars (via `token-cost.sh` invocation OR an inline jq computation using rate constants read from env / defaults) and emit a single dollar-primary line. New format (must be byte-identical to `render-cost-line.sh`'s printf output):
   ```
   💰 Cost: TOTAL ~$X.XX — Claude $A.AA, Codex $B.BB, Cursor $C.CC  |  Tokens: <T>k
   ```
   Centralize the format string in a new helper (`scripts/lib-cost-line-format.sh` or similar — see Files to create §10 below if you choose the shared-helper path; otherwise duplicate the printf verbatim and let `test-render-run-summary-format.sh` enforce equality).

10. **`scripts/token-cost.sh`** — fix Bug 2 + Bug 3. Replace the per-vendor blended constant block (currently lines ~10-13: `DEFAULT_CLAUDE_RATE_PER_M=6.00` etc.) with the per-bucket constants block from the issue body's Bug 3 section, including the verification-date comment.

    Extend the CLI to accept per-bucket counts (default 0 each):
    - `--claude-input-tokens N --claude-cache-read-tokens N --claude-cache-write-5m-tokens N --claude-cache-write-1h-tokens N --claude-output-tokens N`
    - `--codex-input-tokens N --codex-cached-input-tokens N --codex-output-tokens N`
    - `--cursor-input-tokens N --cursor-cache-read-tokens N --cursor-output-tokens N`

    Compute per-vendor cost = sum of (bucket × bucket_rate) for each bucket. Emit the same `CLAUDE_COST=`/`CODEX_COST=`/`CURSOR_COST=`/`TOTAL_COST=` KV lines as today.

    Backward-compat fallback: when only the aggregate `--claude-tokens N` (or analogous) is provided, multiply by the legacy blended rate (preserve `LARCH_CLAUDE_RATE_PER_M`/`LARCH_CODEX_RATE_PER_M`/`LARCH_CURSOR_RATE_PER_M` env override; update the default blended fallbacks to conservative cache-heavy estimates `$0.80/M` Claude / `$2.00/M` Codex / `$1.50/M` Cursor — NOT the stale `$6/M`/`$10/M`). Emit a single-line stderr warning when the blended-fallback path fires: `token-cost.sh: WARNING: per-bucket counts unavailable; using blended rate (may overstate by ~3-10x)`.

    Env var precedence: per-bucket env var > legacy blended env var > per-bucket default constant. Add new env vars matching every per-bucket flag.

11. **`scripts/render-cost-line.sh`** — accept the per-bucket flags and pass them through to `token-cost.sh`. Keep `--claude-tokens N` etc. as backward-compat fallbacks. Update the printed cost line to use the per-bucket-derived TOTAL_COST and per-vendor amounts. Preserve `--quiet-on-empty` behavior. The output format remains exactly:
    ```
    💰 Cost: TOTAL ~$X.XX — Claude $A.AA, Codex $B.BB, Cursor $C.CC  |  Tokens: <T>k
    ```

12. **`scripts/render-run-summary.sh`** — fix Bug 4:
    - Accept the same per-bucket flags as `render-cost-line.sh`. Pass them through to `token-cost.sh` for cost computation. Keep aggregate `--claude-tokens N` etc. as backward-compat fallbacks.
    - In the markdown body composition (around lines 188-195, search for `printf -- '- **Tokens**:` and `printf -- '- **Cost**:`):
      - **Remove** the `- **Tokens**:` bullet entirely.
      - **Replace** the `- **Cost**:` bullet with a single bullet matching the format:
        ```
        - **Cost**: 💰 TOTAL ~$X.XX — Claude $A.AA, Codex $B.BB, Cursor $C.CC  |  Tokens: <T>k
        ```
        (Note: the `- **Cost**:` prefix is the markdown-bullet wrapper around the same dollar-primary line that `render-cost-line.sh` emits.)
    - Update `cost_bullet()` to produce the new format string with the prefixed emoji and the `| Tokens: <T>k` suffix.
    - Preserve the N/A handling: when total cost is "N/A" (cost computation failed), emit `- **Cost**: N/A` and skip the dollar/token rendering.

13. **`scripts/run-step5-review.sh`** — no change. (Listed only to clarify: this script is unrelated to the cost pipeline.)

14. **All current call sites of `render-cost-line.sh` and `render-run-summary.sh`** — `grep -rln 'render-cost-line.sh' .` and `grep -rln 'render-run-summary' .` should return at least:
    - `skills/design/SKILL.md` Step 0b "Terminal cost line" fenced bash block (for render-cost-line).
    - `skills/implement/SKILL.md` Step 17 final-report section (for render-run-summary via write-final-report.sh).
    - `skills/implement/scripts/write-final-report.sh` (calls render-run-summary.sh).
    - `skills/fix-issue/scripts/write-final-report.sh` or equivalent if it exists.
    - Any other site discovered by the grep.

    Update each to read per-bucket counts from the (deduped) `scripts/token-report.sh --format json` BUCKETS_* block and pass them through. After each call-site rewrite, verify with the new structure tests.

15. **`skills/implement/SKILL.md` Step 17 final-report section** (around lines 1769-1824):
    - Update the inline directive about chat-summary printing. The new format (after bug-4): when `LARCH_VERBOSE_TOKENS=true`, print the full per-step table; otherwise the agent prints exactly what `token-report.sh --summary` returns (which is now the dollar-primary single line). Make explicit: "Do NOT paraphrase the summary line — print it verbatim."
    - Update the `render-run-summary.sh` invocation in `write-final-report.sh` to pass per-bucket counts (covered by file modification §16 below).

16. **`skills/implement/scripts/write-final-report.sh`** — pass per-bucket counts to `render-run-summary.sh` (via the new flags introduced by bug-4 file §12). Read per-bucket counts from `token-report.sh --format json` (or `--buckets --vendor <name>`) and forward them as CLI args. Preserve all existing behavior for tracking-issue upsert and `STATUS=`/`COMMENT_URL=` envelope.

17. **`skills/fix-issue/SKILL.md`** and **`skills/fix-issue/scripts/write-final-report.sh`** (if present) — apply the same Step 17 prose update and the same per-bucket forwarding as `/implement`. Grep `skills/fix-issue/` for `token-report.sh --summary` and `render-run-summary.sh` invocations.

### Files to modify — script-md siblings

18. **`scripts/token-cost.md`** — document the per-bucket flag set, env var precedence ladder, default rate sources (with the 2026-05-22 verification date), the blended-fallback warning, and the FAQ entries.

19. **`scripts/token-report.md`** — document the deduplication semantic (`group_by((.rid, .mid)) | map(.[0])`), the new `--buckets --vendor <name>` CLI mode, the new `BUCKETS_*` block in `--format json` output, AND the dollar-primary `--summary` line format.

20. **`scripts/render-cost-line.md`** — document the per-bucket pass-through behavior.

21. **`scripts/render-run-summary.md`** — document the new single-bullet **Cost** line, the dropped **Tokens** bullet, and the per-bucket flag set.

### Files to modify — `/larch:report-tokens` skill

22. **`skills/report-tokens/SKILL.md`** (and any supporting helper scripts under `skills/report-tokens/scripts/`) — re-render historical run-log cost numbers using the corrected pipeline. The skill reads existing `larch-logs/implement/<RUN_ID>/manifest.json` and `token-report.json` files, applies the dedup + per-bucket rates retroactively (recomputes from raw bucket counts, not from the saved aggregate cost), and emits an "Estimated actual cost" column alongside the historical "Reported cost" column for backward visibility. Add regression coverage via `skills/report-tokens/scripts/test-report-tokens-recompute.sh` using a fixture run-log.

### Files NOT to modify

- `SECURITY.md` and `AGENTS.md` — cost reporting is observational, not a trust-boundary surface; no policy change.
- Issue #2382 body text — leave as-is (relative architectural argument unaffected).
- `scripts/token-claude-source.sh` — unchanged. Transcript-selection logic is correct.

## Acceptance

This change is accepted when ALL of the following are true:

1. **Dedup verified**: `scripts/token-report.sh --format json` for the same fixture transcript produces deduped per-bucket counts matching the ground-truth values. For the May 22 #2382 session transcript (or any fixture with known duplicate ratio): `cache_read=19443322 cache_create=473576 output=160117 input=97 total=20077112` (NOT the 47M+ pre-dedup value). `scripts/test-token-report-dedup.sh` ships a fixture jsonl and asserts the deduped count matches a hand-computed expected value.

2. **Per-bucket cost computation verified**: `scripts/test-token-cost-per-bucket.sh` covers the `CLAUDE_COST=5.75` arithmetic case, per-bucket env var overrides, legacy blended env var fallback with stderr warning, and malformed-env-var fallback.

3. **End-to-end cost line matches reality within 10%** for a known test session: `scripts/test-render-cost-line-realism.sh` replays a saved transcript fixture (~$17.16 reference for the May 22 #2382 session) and asserts the rendered line's TOTAL is within ±10%. Skip if fixture is absent.

4. **All current `render-cost-line.sh` AND `render-run-summary.sh` call sites updated**: `scripts/test-render-cost-line-callsites.sh` AND `scripts/test-render-run-summary-callsites.sh` pass.

5. **`/larch:report-tokens` skill updated**: re-renders historical run-log cost numbers using the corrected pipeline with both legacy and recomputed cost columns. Regression test in `skills/report-tokens/scripts/test-report-tokens-recompute.sh` uses a fixture run-log.

6. **Backward compat preserved**: every existing call site that passes only `--claude-tokens N` still produces a usable cost line (the blended-fallback path) with the stderr warning. No call site is broken by the change. Existing tests `scripts/test-token-cost.sh` continue to pass — extend rather than rewrite.

7. **Documentation updated** (`scripts/token-cost.md`, `scripts/token-report.md`, `scripts/render-cost-line.md`, `scripts/render-run-summary.md`). `SECURITY.md`/`AGENTS.md` unchanged.

8. **`make lint` and `bash scripts/relevant-checks.sh` pass cleanly** on the resulting branch. Existing harness coverage stays green; new harnesses wired into `scripts/relevant-checks.sh`.

9. **Anchor comments / fixed surfaces preserved**: `LARCH_DEBUG_TOKEN_REPORT` allowlist + `unavailable` failure-mode contract on `token-report.sh` untouched.

10. **`/implement` and `/fix-issue` final report uses dollar-primary format with per-vendor breakdown** (bug-4):
    - `scripts/render-run-summary.sh` produces a single **Cost** bullet matching: `- **Cost**: 💰 TOTAL ~$X.XX — Claude $A.AA, Codex $B.BB, Cursor $C.CC  |  Tokens: <T>k`. NO standalone `- **Tokens**:` bullet remains.
    - `scripts/token-report.sh --summary` outputs a single line matching: `💰 Cost: TOTAL ~$X.XX — Claude $A.AA, Codex $B.BB, Cursor $C.CC  |  Tokens: <T>k` (byte-identical format string as `render-cost-line.sh`).
    - `skills/implement/SKILL.md` Step 17 prose instructs the agent to print the `--summary` line verbatim (no paraphrasing).
    - `scripts/test-render-run-summary-format.sh` and `scripts/test-token-report-summary-format.sh` pass.
    - Existing `scripts/test-render-run-summary.sh` extended to cover the new format.

## Edge cases

- **Empty / corrupt transcript**: dedup pipeline handles `(requestId, message.id)` both being null/empty (early bootstrap rows). `group_by((.rid // "") + "|" + (.mid // ""))` correctly groups all such rows together; `map(.[0])` takes one representative. Conservative under-count of bootstrap overhead — never over-counts.
- **Mixed-model session**: Opus main + Sonnet subagent — both transcripts summed at Opus rates by default. Document as known approximation (subagent transcripts typically <5% of total).
- **`LARCH_CLAUDE_RATE_PER_M=0` set explicitly**: existing `rate_or_default()` treats as malformed; falls back to default. Preserve.
- **`render-cost-line.sh` / `render-run-summary.sh` with `--quiet-on-empty` + all-zero buckets**: existing short-circuit preserved.
- **`render-run-summary.sh` cost N/A** (cost computation failed): emit `- **Cost**: N/A`, skip the dollar/token rendering. Do NOT emit a malformed partial line.
- **`/implement` agent paraphrasing**: the SKILL.md Step 17 directive must explicitly say "print the --summary line verbatim" so the agent doesn't reformat. The line is structured for chat consumption after bug-4 lands.

## Failure modes (top 3)

1. **Group-by dedup over-collapses early-bootstrap rows lacking `requestId`/`message.id`**. Earliest warning: a unit test in `test-token-report-dedup.sh` that includes 2-3 rows with null `requestId`/null `message.id` and asserts non-over-collapse when usage values differ. Mitigation: take-first-of-group is conservative for usage purposes; documented as known approximation.
2. **Per-bucket env var precedence drift between scripts**: `token-cost.sh`, `render-cost-line.sh`, `render-run-summary.sh`, `token-report.sh --summary`, `/larch:report-tokens` may each implement the env var ladder slightly differently. Mitigation: centralize the precedence logic in a single helper function inside `token-cost.sh` (e.g., `resolve_rate_for_bucket(vendor, bucket)`) and have all other surfaces call `token-cost.sh` only. Pin precedence in `test-token-cost-per-bucket.sh`.
3. **Stale defaults silently in production**: nothing alerts when vendor pricing changes upstream. Mitigation: include verification date in source-attribution comment; calendar reminder pattern in `.md` doc ("review annually each May"); document env override as operator escape hatch.

## Testing strategy

- New harnesses (8 listed above) wired into `scripts/relevant-checks.sh` and `make lint`.
- Existing harnesses for `token-cost.sh`, `token-report.sh`, `render-cost-line.sh`, `render-run-summary.sh` stay green; extend rather than rewrite.
- Smoke test against the live transcript at PR-time: re-run `/design --simple <some-issue>` AND `/implement <some-issue>` after merging, confirm both printed cost lines match the Anthropic Console billing within ±10%. Document the Console-comparison procedure in `scripts/token-cost.md`.

## Out of scope

- Anthropic Bedrock / Vertex AI pricing variants. Documented at source URLs.
- OpenAI's "credits"/"CCU" billing for ChatGPT subscriptions.
- Real-time price fetches.
- Volume discount tiers.
- Fast-mode premium pricing — env override only.
- Batch API 50% discount — env override only.
- Updating issue #2382's body text.

## Diff size estimate

- `scripts/token-report.sh`: ~80 added (jq dedup + `--buckets --vendor` mode + BUCKETS_* JSON block + dollar-primary `--summary` line), ~15 modified
- `scripts/token-cost.sh`: ~130 added (per-bucket constants + flags + compute + blended-fallback warning + env precedence helper), ~15 removed (stale constants), ~20 modified
- `scripts/render-cost-line.sh`: ~30 added (per-bucket pass-through), ~5 modified
- `scripts/render-run-summary.sh`: ~50 added (per-bucket flags + cost_bullet rewrite + Tokens-bullet drop), ~10 removed (Tokens bullet)
- `scripts/token-cost.md`: ~80 added
- `scripts/token-report.md`: ~60 added (dedup + buckets + dollar-primary summary)
- `scripts/render-cost-line.md`: ~20 added
- `scripts/render-run-summary.md`: ~40 added (new format)
- `skills/design/SKILL.md`: ~15 modified (terminal cost line call site)
- `skills/implement/SKILL.md`: ~25 modified (Step 17 prose + write-final-report.sh args)
- `skills/implement/scripts/write-final-report.sh`: ~25 added (per-bucket forwarding)
- `skills/fix-issue/*`: ~25 modified (parallel updates if /fix-issue has the surface)
- `skills/report-tokens/SKILL.md`: ~60 added (re-render path), ~10 modified
- `skills/report-tokens/scripts/test-report-tokens-recompute.sh`: ~80 added (NEW)
- `scripts/test-token-report-dedup.sh`: ~80 added (NEW)
- `scripts/test-token-cost-per-bucket.sh`: ~120 added (NEW)
- `scripts/test-render-cost-line-realism.sh`: ~50 added (NEW)
- `scripts/test-render-cost-line-callsites.sh`: ~40 added (NEW)
- `scripts/test-render-run-summary-callsites.sh`: ~40 added (NEW)
- `scripts/test-render-run-summary-format.sh`: ~50 added (NEW)
- `scripts/test-token-report-summary-format.sh`: ~40 added (NEW)
- `scripts/test-token-cost.sh`: ~50 added (extended)
- `scripts/test-render-run-summary.sh`: ~30 added (extended for new format)
- `scripts/relevant-checks.sh`: ~10 modified (wire new harnesses)
- `Makefile`: ~16 modified (new lint targets)

diff_lines: 1200

## Test plan
(no test plan section in plan-file)
