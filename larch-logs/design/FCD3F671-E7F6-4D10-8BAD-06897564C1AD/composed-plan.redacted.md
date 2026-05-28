## Plan

Fix `/design` plan-revise auto-apply by combining three small changes (A+B+C from issue #3146) and adding one new tier-4 file-replacement fallback inside `revise-plan-with-waterfall.sh`. Update the two consumer surfaces (`plan-review-loop.sh` and `plan-review.md`) so the new `REVISE_STATUS=ok-fallback` value reads as success and propagates intact.

### UPDATED: `skills/design/scripts/revise-plan-with-waterfall.sh`

Six surgical edits, all inside the existing script (no new files):

1. **State extension.** Add `tier4_status=""` next to the existing `tier1_status` / `tier2_status` / `tier3_status` declarations. Add `winner_is_fallback=false` next to `winner=""`. Extend the `case` statements in `set_tier_status()` and `get_tier_status()` to accept ordinal `4`. For ordinal `4`, `set_tier_status` delegates to a new `merge_tier4_status` helper (see edit 6) so later mini-waterfall attempts cannot downgrade an earlier failure.

2. **Preamble + fence strip in `extract_patch()`.** Replace the current first-line / last-line ```diff fence check with an awk pass that runs only when `PATCH_FORMAT == "unified-diff"`. The awk drops every leading line until the first one that matches `^```diff$`, `^diff --git `, `^--- `, `^\+\+\+ `, or `^@@ `; the ```diff opener is consumed (`next`), the diff-header opener is included. After that point it copies every line except a standalone ``` line. For `PATCH_FORMAT == "file-replacement"` the existing `cp "$output" "$patch"` stays unchanged.

3. **`--recount` on `git apply`.** Add `--recount` to the `git apply --check --whitespace=nowarn` invocation in `check_git_apply()` and to the `git apply --whitespace=nowarn` invocation in `apply_patch_file()` (unified-diff branch only). Git has supported `--recount` since 2.0.

4. **Tier-4 fallback chain (after the existing tier-1..3 chain).** Append a block that gates on `[[ "$PATCH_FORMAT" == "unified-diff" && -z "$winner" ]]`, sets `PATCH_FORMAT="file-replacement"` / `winner_is_fallback=true`, re-renders the prompt via `compose_prompt`, then runs an internal Codex → Cursor → Claude mini-waterfall via `attempt_tier 4 <tool> "$REVISE_DIR/<tool>-output.txt"`. The fallback **reuses existing artifact names** (`<tool>-output.txt` and `prompt.txt`); no new filenames are introduced, so `scripts/lib-design-round-artifacts.sh`'s allowlist does not change and `REVISE_PATCH_PATH=$REVISE_DIR/$winner-output.txt` stays correct without conditional branches. Tier-1..3 raw outputs are overwritten by tier 4 when it fires; per-tier 1..3 statuses survive in `REVISE_TIER_1/2/3_STATUS`.

5. **`finalize()` aggregation.** Read `tier4_status` (default `not-attempted`) and emit `REVISE_TIER_4_STATUS=$status4`. Extend the substring checks that compute `final_status` to include `$status4` alongside `$status1 $status2 $status3`. When `$winner` is non-empty, emit `REVISE_STATUS=ok-fallback` if `winner_is_fallback == true`; otherwise emit `REVISE_STATUS=ok` (existing behavior).

6. **`merge_tier4_status()` helper (new function, called only from `set_tier_status` for ordinal 4).** Defines severity precedence (best → worst): `ok > emit-plan-failed > apply-failed > invalid-patch > no-patch > skipped-not-present > not-attempted`. If `tier4_status == "ok"`, ignore the new value (winner sticks). Else if the new value is `ok`, set `tier4_status="ok"`. Else keep whichever rank is more severe so a later `no-patch` or `skipped-not-present` never downgrades an earlier `invalid-patch` / `apply-failed` / `emit-plan-failed`. Implemented with a `case` block on `$tier4_status:$new`. Pure Bash 3.2.

### UPDATED: `skills/design/scripts/revise-plan-with-waterfall.md`

- Extend the documented `REVISE_STATUS` enum to `ok | ok-fallback | failed-no-patch | failed-validation | failed-apply` and define `ok-fallback` as "tier-4 file-replacement fallback applied successfully".
- Add a "Tier 4 (file-replacement fallback)" paragraph (when it fires, Codex → Cursor → Claude mini-waterfall, artifact-reuse note).
- Document the new `REVISE_TIER_4_STATUS` key and the `merge_tier4_status` severity-precedence rule.

### UPDATED: `skills/design/scripts/plan-review-loop.sh`

Two-line consumer fix:

- In `_run_revise_with_status_parse()` (~line 489), replace `[[ "$revise_status" == "ok" ]] && return 0` with `[[ "$revise_status" == "ok" || "$revise_status" == "ok-fallback" ]] && return 0`.
- At line 1298 in the round-management body, replace the unconditional `revise_status=ok` with `revise_status="${revise_status:-ok}"` so an `ok-fallback` value parsed earlier propagates through to `round-summary.env`, the stdout KV emit, and `.step3-plan-review-result.env`.

### UPDATED: `skills/design/references/plan-review.md`

Update the "Revision failures" bullet so it reads "non-zero revise rc or `REVISE_STATUS` not in (`ok`, `ok-fallback`)" instead of "other than `ok`".

## Acceptance

- `bash scripts/test-revise-plan-with-waterfall.sh` passes all nine existing cases unchanged; `REVISE_TIER_4_STATUS` appears as an additional KV in every case.
- `bash skills/design/scripts/test-plan-review-loop.sh` passes; the relaxed conditional and the `${revise_status:-ok}` form preserve the existing `REVISE_STATUS=ok` / `REVISE_STATUS=failed-*` flows used by the harness stubs.
- `make lint` passes (bash-3.2, script-md-siblings, renderer-substitution-safety).
- Manual smoke test: a `/design --simple` run on a small issue where tier-1 Codex succeeds at unified-diff still emits `REVISE_STATUS=ok` end-to-end (not `ok-fallback`).
- Manual fallback test (or live run): a `/design --simple` run where all three unified-diff tiers fail `git apply --check` triggers tier-4, tier-4 succeeds with file-replacement, `REVISE_STATUS=ok-fallback` propagates through `round-summary.env` and `.step3-plan-review-result.env`, and the multi-round loop continues instead of reporting `LOOP_STATUS=revision-failed`.

diff_lines: 95
