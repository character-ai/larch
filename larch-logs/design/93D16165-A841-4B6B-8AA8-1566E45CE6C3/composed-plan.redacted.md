## Plan

# Implementation Plan — issue #2900: Three orphan small script fixes

Combined PR landing three independent OOS items: a parser bug fix (Item A, severity *important*), a Codex telemetry capture refactor across 3 non-launcher sites (Item B, severity latent), and a one-line allowlist addition (Item C, severity latent). All Round 1 user decisions are encoded as binding constraints. The plan was revised based on 14 accepted findings from the plan-review panel.

## Approach

**Item A (parser fix)** — In `scripts/get-issue-state.sh:35-44`, the `--issue` and `--repo` branches assume `${2:-}` then `shift 2` — with `set -u` (no `-e`), missing-value as final argv yields infinite loop. Fix: insert a guard inside each `case` branch BEFORE the `${2:-}` assignment and `shift 2` that rejects BOTH (a) missing value (arity `[ $# -lt 2 ]`) AND (b) a flag-looking next token (`case "${2:-}" in --*) reject ;; esac`). On either rejection, emit `FAILED=true` / `ERROR=<flag> requires a value` envelope (matching the existing unknown-flag branch at lines 39-42) and `exit 1`. Keep `set -uo pipefail` unchanged.

**Item B (Codex telemetry capture at 3 non-launcher sites)** — Mirror the prior-art at `scripts/launch-codex-implement.sh:317-338` and `scripts/launch-codex-ci.sh:172-230`. Per-site invariants:

1. **PLUGIN_ROOT discovery**: At the top of `lint-fix-loop.sh` and `run-negotiation-round.sh` (and `review-and-fix.sh` if not already defined), add `PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd -P)}"` immediately after `SCRIPT_DIR` is established. Without this, telemetry calls hit unbound-variable under `set -u`.
2. **Source `lib-codex-launcher-common.sh`** at each site that doesn't already source it (lint-fix-loop.sh and review-and-fix.sh currently source `lib-cursor-launcher-common.sh` only; run-negotiation-round.sh already sources `lib-external-launcher-common.sh` which exposes the same `external_launcher_record_usage_from_events` — use that name there directly).
3. **Codex argv changes**: add `--json`; add `--output-last-message "$LEGACY_LOG"` (preserves the previously-captured final message that the wrapper.log used to receive); add `--` separator before the prompt body.
4. **Drop `--capture-stdout`** from the `RUN_EXTERNAL_AGENT_SH` invocation (lint-fix-loop, review-and-fix) — it consolidates stdout into wrapper.log which is what produces the combined-stream shape the OOS flags. Replace with explicit shell `>"$EVENTS_FILE"` stdout redirect; keep wrapper.log retaining stderr-shaped content (via the wrapper's own diagnostic stream).
5. **Exit-code preservation**: wrap the codex call as `codex_rc=0; <codex call> || codex_rc=$?; <telemetry call>; return "$codex_rc"`. The telemetry call MUST be best-effort (its exit must not overwrite codex's exit). This pattern also records usage for FAILED Codex attempts (events.jsonl is produced before the failure exit).
6. **Telemetry call**: `codex_launcher_record_usage_from_events "$PLUGIN_ROOT" "$EVENTS_FILE" "$SIDECAR_LOG" "<RAW_BUCKET_LABEL>"` (or `external_launcher_record_usage_from_events` at the negotiation site).

**Raw bucket labels (UNDERSCORE form, for token-ledger row attribution)** — matches the existing token-ledger convention seen in launchers:
- `review-and-fix.sh:257` → raw label `codex_review_fix`, events at `$round_dir/coder-codex.events.jsonl`, legacy log `$round_dir/coder-codex.log`, sidecar `$round_dir/coder-codex.sidecar` (matches launch-codex-ci.sh:171 pattern).
- `lint-fix-loop.sh:223` → raw label `codex_lint_fix`, events at `$run_dir/codex.events.jsonl`, legacy log `$run_dir/codex.log`, sidecar `$run_dir/codex.sidecar`.
- `run-negotiation-round.sh:84` → raw label `codex_negotiation`, events at `${OUTPUT_FILE%.txt}.events.jsonl`, legacy `OUTPUT_FILE` unchanged (already in argv), sidecar `${OUTPUT_FILE%.txt}.sidecar`.

**Architectural decision — events.jsonl publication (FINDING_14 resolution, revises Round 1 Decision 4)** — Round 1 said "add events.jsonl to round_artifact_included." Plan-review surfaced that raw Codex `events.jsonl` files contain prompts, reviewer text, repo snippets, response bodies, and tool output — not just token counters. Publishing them into committed public run-logs is a content-leakage risk. The existing `*.events.jsonl` exclusion at `scripts/larch-log.sh:70` was deliberate; reversing it without sanitization would leak content. **Resolution**: keep the existing `*.events.jsonl` exclusion UNTOUCHED. The new events.jsonl files use the natural `.events.jsonl` naming (matching launcher convention) and remain LOCAL — they exist for `codex_launcher_record_usage_from_events` consumption only. The per-bucket telemetry is captured in the sanitized `larch-tokens-*.jsonl` token ledger and is what downstream consumers should read. This is a deliberate revision of Round 1 Decision 4 prompted by the security finding; the user has accepted FINDING_14 by selecting "Apply all" at Gate B.

**Item C (allowlist add)** — Strict single-literal `scout-archetype-yield.tsv` insertion into the include alternation at `scripts/larch-log.sh:89`. No broader sweep. Item C remains unchanged from the original plan.

**Timing ledger entries (FINDING_8 resolution)** — The original plan added 3 `codex-*` slugs to `TIMING_TASK_KINDS_ALLOWED` in `scripts/lib-timing-kinds.sh`, but no `timing-ledger.sh record-vendor-task` calls were planned at the 3 sites. The allowlist entries would be unused. Resolution: **drop the lib-timing-kinds.sh additions** from the plan. The 3 telemetry pathways write to the token-ledger only (via `codex_launcher_record_usage_from_events` → underscore raw bucket label). The hyphen-form `--timing-task-kind` slugs are not needed because no `timing-ledger.sh record-vendor-task` calls are added. `scripts/lib-timing-kinds.sh` and its `.md` sibling are NOT modified.

**Non-goals (Round 1 Decisions 6 + 7)**: Keep `set -uo pipefail` in `get-issue-state.sh`. Do NOT modify Cursor fallback paths in the 3 Item B files. Do NOT modify `scripts/check-reviewers.sh:199`. Do NOT modify launcher sites that already use `--json`.

## Files to modify/create

### UPDATED: `scripts/get-issue-state.sh`

Item A. Inside the `while [ $# -gt 0 ]` loop at lines 35-44, BEFORE the `${2:-}` assignment in the `--issue` and `--repo` `case` branches, insert a value-required guard that rejects BOTH missing arity AND a flag-looking next token. Example shape for each branch:

```bash
--issue)
    if [ $# -lt 2 ]; then
        emit_kv FAILED true; emit_kv ERROR "--issue requires a value"; exit 1
    fi
    case "$2" in
        --*) emit_kv FAILED true; emit_kv ERROR "--issue requires a value"; exit 1 ;;
    esac
    ISSUE="$2"; shift 2 ;;
```

Apply symmetric guard for `--repo`. Error messages remain on a single line (KV envelope). Keep `set -uo pipefail`; do NOT switch to `-euo pipefail`.

### UPDATED: `scripts/get-issue-state.md`

Document the two new error envelope reasons (`--issue requires a value`, `--repo requires a value`) and the flag-looking-next-token rejection rule. One-paragraph update under exit conditions.

### UPDATED: `scripts/lint-fix-loop.sh`

Item B. Changes:
1. Near the top (after `SCRIPT_DIR` is set), add `PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd -P)}"`.
2. Source `lib-codex-launcher-common.sh` (adjacent to the existing `lib-cursor-launcher-common.sh` source at lines 10-12).
3. In `run_codex()` (lines 220-226):
   - Define `local codex_events="$run_dir/codex.events.jsonl"`.
   - Define `local codex_sidecar="$run_dir/codex.sidecar"` (or reuse the wrapper's existing sidecar path if present).
   - Restructure as: `local codex_rc=0` + wrapper call with `--json`, `--output-last-message "$run_dir/codex.log"`, `--` separator, dropped `--capture-stdout`, shell-redirect `>"$codex_events" 2>"$run_dir/codex.wrapper.log"` + `|| codex_rc=$?` + telemetry call + `return "$codex_rc"`.
   - Telemetry: `codex_launcher_record_usage_from_events "$PLUGIN_ROOT" "$codex_events" "$codex_sidecar" "codex_lint_fix"` (best-effort; do not affect exit code).
4. Do NOT modify `run_cursor()` (Round 1 Decision 7).

### UPDATED: `scripts/lint-fix-loop.md`

Document the new local-only `codex.events.jsonl` artifact (not published — matches existing launcher convention), the `codex_lint_fix` token-ledger bucket label, the `--output-last-message` requirement, and the exit-code-preservation contract for `run_codex()`. One-paragraph update.

### UPDATED: `scripts/run-negotiation-round.sh`

Item B. The codex branch at lines 84-86 already calls `codex exec` directly (no `RUN_EXTERNAL_AGENT_SH` wrapper) and already uses `--output-last-message "$OUTPUT_FILE"`. Changes:
1. Near the top (after `SCRIPT_DIR` set), add `PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd -P)}"`. The script already sources `lib-external-launcher-common.sh:33-34` — no new source needed; use `external_launcher_record_usage_from_events` directly.
2. Define `local codex_events="${OUTPUT_FILE%.txt}.events.jsonl"` and `local codex_sidecar="${OUTPUT_FILE%.txt}.sidecar"` near the case-branch start. `rm -f "$codex_events" "$codex_sidecar"` immediately before the codex call so stale prior-run artifacts cannot be re-read.
3. Add `--json` and `--` separator to the `codex exec` argv. Replace the trailing `2>&1` with `>"$codex_events" 2>"$codex_sidecar"` (splits streams; preserves the existing `--output-last-message "$OUTPUT_FILE"` for the final response).
4. Wrap as `codex_rc=0; codex exec ... || codex_rc=$?; external_launcher_record_usage_from_events "$PLUGIN_ROOT" "$codex_events" "$codex_sidecar" "codex_negotiation" || true; return "$codex_rc"` (or `exit "$codex_rc"` depending on the surrounding control flow — preserve existing reviewer-failure exit semantics).
5. Do NOT modify the `cursor` branch (Round 1 Decision 7).

### UPDATED: `scripts/run-negotiation-round.md`

Document the new local-only `<output-base>.events.jsonl` artifact, the `<output-base>.sidecar` stderr capture, the `codex_negotiation` token-ledger bucket, exit-code preservation, and the explicit `rm -f` before codex re-run. One-paragraph update.

### UPDATED: `skills/review-and-fix/scripts/review-and-fix.sh`

Item B. The script's top-of-file source list at line ~30 currently sources `lib-cursor-launcher-common.sh`. Changes:
1. Verify `PLUGIN_ROOT` is already defined here (the script uses `$PLUGIN_ROOT` at line ~30: `source "$PLUGIN_ROOT/scripts/lib-cursor-launcher-common.sh"`). It is. No new PLUGIN_ROOT definition needed at this site.
2. Add `source "$PLUGIN_ROOT/scripts/lib-codex-launcher-common.sh"` alongside the existing cursor sibling.
3. In `run_coder_dispatch()` codex branch (lines 254-261):
   - Define `local codex_events="$round_dir/coder-codex.events.jsonl"` and `local codex_sidecar="$round_dir/coder-codex.sidecar"`.
   - Restructure as: `local codex_rc=0` + wrapper call with `--json`, `--output-last-message "$round_dir/coder-codex.log"`, `--` separator, dropped `--capture-stdout`, shell-redirect `>"$codex_events" 2>"$round_dir/coder-codex.wrapper.log"` + `|| codex_rc=$?`.
   - Telemetry (best-effort, runs on both success and failure paths so failed attempts that produced events are still recorded): `codex_launcher_record_usage_from_events "$PLUGIN_ROOT" "$codex_events" "$codex_sidecar" "codex_review_fix" || true`.
   - On `codex_rc == 0`: keep existing success bookkeeping (`cp ... tool_log`, `printf codex > tool_stdout`, `return 0`). On `codex_rc != 0`: fall through to the existing Cursor fallback at line 263. Preserve current cascade semantics.
4. Do NOT modify the Cursor branch (lines 263-280).

### UPDATED: `skills/review-and-fix/scripts/review-and-fix.md`

Document the new local-only `coder-codex.events.jsonl` artifact, the `coder-codex.sidecar` stderr capture, the `codex_review_fix` token-ledger bucket, exit-code preservation, and best-effort telemetry on failed-attempt paths. One-paragraph update.

### UPDATED: `scripts/larch-log.sh`

Item C only. ONE literal addition to `round_artifact_included()` at line 89 (alongside `findings-classification.tsv`): `scout-archetype-yield.tsv|`. Keep the existing `*.events.jsonl` exclusion at line 70 UNTOUCHED — the new Item B `.events.jsonl` artifacts are intentionally NOT published (FINDING_14 resolution).

### UPDATED: `scripts/larch-log.md`

Update the documented allowlist to list `scout-archetype-yield.tsv`. Add an explicit prose note that `*.events.jsonl` files (including the new Item B `codex.events.jsonl` / `coder-codex.events.jsonl` artifacts) remain excluded by design (content-leakage prevention — the events stream may contain prompts/responses/repo snippets; per-bucket telemetry is captured in the sanitized token ledger instead).

### UPDATED: `SECURITY.md`

Add a one-paragraph note distinguishing two artifact families:
- **Excluded from committed run-logs**: `*.events.jsonl` raw Codex event streams (launcher-generated `${TRANSCRIPT_PATH}.events.jsonl`, plus the new non-launcher events at `coder-codex.events.jsonl`, `codex.events.jsonl`, `${OUTPUT_FILE%.txt}.events.jsonl`). These contain prompts, reviewer text, repo snippets, response bodies, tool output.
- **Included (sanitized)**: per-bucket telemetry rows in `larch-tokens-*.jsonl` (passed through `external_launcher_record_usage_from_events` which extracts only usage counters).

### UPDATED: `scripts/test-get-issue-state.sh`

Item A regression. Add new cases after existing case `(g) gh_success` (around line 125), using fresh labels `(h)` and `(i)` (NOT reusing existing labels per FINDING_1):
- `(h) --issue with no value as final argv` — invoke `get-issue-state.sh --issue` (no following value). Assert: exits 1 within ≤5s (wrap in `timeout 5s`), stdout contains `FAILED=true` and `ERROR=--issue requires a value`, no shift-error spam in stderr.
- `(i) --repo with no value as final argv` — symmetric: invoke `get-issue-state.sh --issue 12 --repo` (no following value). Assert: exit 1 + `ERROR=--repo requires a value` within 5s.
- `(j) --issue with flag-looking next token` — invoke `get-issue-state.sh --issue --repo upstream/repo`. Assert: exit 1 + `ERROR=--issue requires a value` (FINDING_13).
- `(k) --repo with flag-looking next token` — invoke `get-issue-state.sh --issue 12 --repo --some-flag`. Assert: exit 1 + `ERROR=--repo requires a value`.

### UPDATED: `scripts/test-lint-fix-loop.sh`

Item B regression. The harness currently uses a `RUN_EXTERNAL_AGENT` wrapper stub (no `STUB_BIN/codex` fixture). Add a dedicated case that simulates `run_codex`:
- Build a wrapper-stub that, when invoked with `--json` in the forwarded argv, writes a minimal synthetic JSONL event to stdout (the same stream the production wrapper would redirect to events.jsonl). The stub also honors `--output-last-message <path>` by writing a small final-message string to that path.
- Set `LARCH_TOKEN_LEDGER="$TMPROOT/token-ledger.jsonl"` for the case (isolated path).
- Run `run_codex` via the harness's existing invocation pattern.
- Assert: `$run_dir/codex.events.jsonl` is non-empty; `$run_dir/codex.log` contains the synthetic final message; `$run_dir/codex.wrapper.log` is created and does NOT contain the JSONL content (preserves wrapper.log shape); `$TMPROOT/token-ledger.jsonl` contains a row with `vendor=codex` and raw bucket label `codex_lint_fix` and non-zero usage counters (FINDING_15).
- Add a failing-codex variant: stub exits non-zero after writing the events; assert events still captured and ledger row still written, AND `run_codex` returns the non-zero exit (exit-code preservation; FINDING_10, FINDING_12).
- Add a `CLAUDE_PLUGIN_ROOT-unset` variant: unset the env var and verify the script's `PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-...}"` fallback resolves correctly (FINDING_4).

### UPDATED: `scripts/test-run-negotiation-round.sh`

Item B regression. The harness uses a `STUB_BIN/codex` fixture (visible at the `STUB_BIN` block in the existing file). Extend that stub to forward `--json` (write synthetic JSONL events to stdout) and `--output-last-message <path>` (write final message to path). Add a case:
- Set `LARCH_TOKEN_LEDGER` to an isolated path.
- Invoke the codex branch.
- Assert: `${OUTPUT_FILE%.txt}.events.jsonl` non-empty; `${OUTPUT_FILE%.txt}.sidecar` exists; `$OUTPUT_FILE` carries the final-message string; token ledger contains a `vendor=codex` / `codex_negotiation` row.
- Add the same failing-codex + exit-code-preservation assertions as test-lint-fix-loop above.
- Add the same `CLAUDE_PLUGIN_ROOT-unset` variant.
- Add a stale-artifacts variant: pre-create `${OUTPUT_FILE%.txt}.events.jsonl` with stale content; invoke; verify the stale content was overwritten (the `rm -f` step works).

### UPDATED: `skills/review-and-fix/scripts/test-review-and-fix.sh`

Item B regression. The harness uses `run-external-agent-stub.sh` (referenced widely; the script lives at `$TMP/run-external-agent-stub.sh` per the harness's setup function). The plan:
- Extend the stub: when `--json` appears in the forwarded argv (i.e., the inner `codex exec --json ...`), write a minimal synthetic JSONL event to stdout (the same stream the production wrapper would redirect via `>"$round_dir/coder-codex.events.jsonl"`). Continue honoring `--output-last-message <path>` by writing a small final-message string to that path. Continue writing existing `APPLIED`-style outputs to whatever current channels the harness asserts on, so existing tests don't break.
- Add a new case in test-review-and-fix.sh:
  - Set `LARCH_TOKEN_LEDGER` to an isolated path.
  - Invoke `run_coder_dispatch` codex branch.
  - Assert: `$round_dir/coder-codex.events.jsonl` is non-empty; `$round_dir/coder-codex.log` contains the synthetic final message; `$round_dir/coder-codex.wrapper.log` does NOT contain JSONL bleed; token ledger has `vendor=codex` / `codex_review_fix` row with non-zero counters.
  - Failing-codex variant + exit-code preservation (the failing branch must still fall through to Cursor fallback per current cascade semantics).

### UPDATED: `scripts/test-larch-log.sh`

Item B + C regression. Add cases:
- `round_artifact_included scout-archetype-yield.tsv` returns 0 (Item C).
- `round_artifact_included foo.events.jsonl` returns 1 (verifies the existing `*.events.jsonl` exclusion still applies — Item B's new artifact names use natural `.events.jsonl` extension, so this assertion covers them too).
- `round_artifact_included coder-codex.events.jsonl` returns 1 (specific Item B file name — confirms it's excluded as expected).
- `round_artifact_included codex.events.jsonl` returns 1 (lint-fix-loop's events file — excluded).
- Optional: extend an existing `test-larch-log-write-round` end-to-end case to stage `scout-archetype-yield.tsv` into a round source directory and confirm it survives publication.

## Edge cases

- **Item A guard placement**: the new value-required check fires BEFORE the `case "$ISSUE"` numeric-validation at line 53. They are sequential, not interleaved.
- **Item A flag-looking value when intentional**: if a user genuinely wants to pass an issue number that looks like `--12345`, they can't. This is intentional: argv `--issue --12345` is a usage error per the OSS body's "missing value" definition. Numeric-only validation at line 53 also rejects non-numeric values, so the user has no legitimate use case for `--`-prefixed argument values.
- **Item B exit-code preservation**: telemetry-call failures (rare — `external_launcher_record_usage_from_events` is robust) MUST NOT overwrite the codex exit code. Always use `|| true` on the telemetry call OR explicitly capture and discard its rc. The `codex_rc` variable is the authoritative return.
- **Item B negotiation site dual-output**: `--output-last-message "$OUTPUT_FILE"` and `--json` to stdout produce TWO codex outputs. Both are preserved by the `> "$codex_events"` stdout redirect (JSONL events) and the `--output-last-message` argument (final message). Verify by reading codex CLI docs and running locally before commit.
- **Item B `rm -f` before run**: must remove stale events.jsonl AND sidecar AND legacy log if reusing a path. Without rm, a previous run's content could leak into the new run's parsing.
- **Item B `--` separator**: codex exec interprets argv tokens starting with `-` as flags. Without `--` before `"$prompt_body"`, a prompt body starting with `-` could be misparsed. Current prompts don't start with `-`, but `--` is cheap insurance.
- **Item C allowlist**: `scout-archetype-yield.tsv` does not match any exclusion at lines 70-87. The literal-basename match at line 89 takes precedence over the `*)` default-deny at line 98.
- **Test isolation**: `LARCH_TOKEN_LEDGER` must be a per-test path (e.g., `"$TMPROOT/token-ledger.jsonl"`) so concurrent harness runs don't contend. The harnesses already use `TMPROOT` mktemp dirs, so this is straightforward.

## Failure modes

1. **`--output-last-message` regression** — If a future change drops `--output-last-message` from one of the 3 sites without also reintroducing `--capture-stdout`, the legacy `coder-codex.log` / `codex.log` becomes empty and any downstream consumer that reads them silently sees no content.
   - *Earliest signal*: the per-site harness assertion `coder-codex.log contains final message text` fails.
   - *Mitigation*: explicit assertions on the legacy log shape; sibling .md documents the `--output-last-message` requirement.

2. **`PLUGIN_ROOT` regression** — If `CLAUDE_PLUGIN_ROOT` is unset AND `SCRIPT_DIR` is mis-resolved (e.g., script invoked via symlink without `pwd -P`), the `$(cd "$SCRIPT_DIR/.." && pwd -P)` fallback may point at the wrong directory, and `lib-codex-launcher-common.sh` source fails with `set -u` aborting the script.
   - *Earliest signal*: the `CLAUDE_PLUGIN_ROOT-unset` test variant exits non-zero.
   - *Mitigation*: explicit harness coverage in the 3 test files; identical fallback pattern across the 3 sites.

3. **JSONL content leakage** — If a future change re-allowlists `*-events.jsonl` (or any specific Item B file) into `round_artifact_included` without first adding a sanitizer that strips prompts/responses/repo content, public run-log commits would leak reviewer text and prompt bodies. This is the failure mode that FINDING_14 prevents.
   - *Earliest signal*: the `round_artifact_included foo.events.jsonl returns 1` regression assertion in test-larch-log.sh fails.
   - *Mitigation*: explicit negative assertions + SECURITY.md prose distinguishing the two artifact families.

## Testing strategy

Per-item regression tests in the same PR (Round 1 Decision 5):

- **Item A**: 4 new cases in `scripts/test-get-issue-state.sh` covering missing-value AND flag-looking-value rejection for both `--issue` and `--repo`. All bounded by `timeout 5s` to catch infinite-loop regressions. Use fresh case labels `(h)` `(i)` `(j)` `(k)` per FINDING_1.

- **Item B** (per site): the 3 harnesses (test-lint-fix-loop, test-run-negotiation-round, test-review-and-fix) each get a Codex test case with these assertions:
  - events.jsonl created and non-empty
  - legacy `*.log` contains the synthetic final-message text (NOT empty)
  - wrapper.log retains stderr-only shape (no JSONL bleed)
  - isolated `LARCH_TOKEN_LEDGER` contains a `vendor=codex` row with the expected underscore bucket label (`codex_lint_fix` / `codex_review_fix` / `codex_negotiation`) and non-zero usage counters
  - failing-codex variant: events captured, telemetry row written, AND non-zero exit propagated (FINDING_10/FINDING_12)
  - `CLAUDE_PLUGIN_ROOT-unset` variant: PLUGIN_ROOT fallback resolves correctly (FINDING_4)
  - Stub harness extensions (FINDING_6, FINDING_7) ensure each stub emits JSONL when `--json` is present and writes `--output-last-message` content to the named path

- **Item B + C (allowlist)**: new cases in `scripts/test-larch-log.sh` asserting Item C's positive case (`scout-archetype-yield.tsv` returns 0) AND Item B's negative cases (`*.events.jsonl` family still excluded, including the specific new file names `coder-codex.events.jsonl` / `codex.events.jsonl` / `<base>.events.jsonl`).

All test harnesses are wired into `make lint` / pre-commit hooks already; no new Makefile targets needed.

Pre-merge verification: `bash scripts/relevant-checks.sh` plus the 5 modified harnesses (`bash scripts/test-get-issue-state.sh`, `bash scripts/test-lint-fix-loop.sh`, `bash scripts/test-run-negotiation-round.sh`, `bash skills/review-and-fix/scripts/test-review-and-fix.sh`, `bash scripts/test-larch-log.sh`).

diff_lines: 400

## Acceptance

The PR is acceptable when ALL of the following hold:

1. **Item A regression test passes**: `scripts/test-get-issue-state.sh` includes cases (h)–(k) covering missing-value AND flag-looking-value rejection for both `--issue` and `--repo`. Each case must complete in ≤5 seconds (`timeout 5s`) — no infinite loop. Each case asserts `FAILED=true` and `ERROR=<flag> requires a value` in stdout, exit code 1.
2. **Item B per-site regression tests pass**: `scripts/test-lint-fix-loop.sh`, `scripts/test-run-negotiation-round.sh`, and `skills/review-and-fix/scripts/test-review-and-fix.sh` each add at least:
   - A success-path case asserting events.jsonl created, legacy `*.log` contains synthetic final message, wrapper.log retains stderr-shape, isolated `LARCH_TOKEN_LEDGER` contains a `vendor=codex` row with the expected underscore bucket label (`codex_lint_fix` / `codex_review_fix` / `codex_negotiation`) and non-zero usage counters.
   - A failing-Codex case asserting events still captured, telemetry recorded, AND non-zero exit propagated.
   - A `CLAUDE_PLUGIN_ROOT`-unset case asserting the `PLUGIN_ROOT` fallback resolves correctly.
   - Stub harness extensions emit JSONL when `--json` is forwarded and honor `--output-last-message`.
3. **Item C regression test passes**: `scripts/test-larch-log.sh` adds:
   - Positive: `round_artifact_included scout-archetype-yield.tsv` returns 0.
   - Negative: `round_artifact_included coder-codex.events.jsonl`, `codex.events.jsonl`, and a representative `<base>.events.jsonl` from the negotiation site all return 1 (the existing `*.events.jsonl` exclusion still applies; raw event files are NOT published).
4. **Wrapper.log shape preserved**: at all 3 Item B sites, `*.wrapper.log` (or `*.sidecar` at the negotiation site) does NOT contain JSONL bleed; it retains the prior stderr-style content shape.
5. **Exit-code preservation verified**: at all 3 Item B sites, the codex wrapper structure is `codex_rc=0; <call> || codex_rc=0; <telemetry best-effort>; return "$codex_rc"`. Telemetry call MUST be best-effort and MUST NOT overwrite the codex exit code.
6. **`PLUGIN_ROOT` defined**: `scripts/lint-fix-loop.sh` and `scripts/run-negotiation-round.sh` define `PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd -P)}"` near `SCRIPT_DIR`. `skills/review-and-fix/scripts/review-and-fix.sh` already defines it.
7. **`codex exec` argv shape (all 3 sites)**: adds `--json`, adds `--output-last-message <legacy-log>`, adds `--` separator before the prompt body. The 2 wrapped sites (lint-fix-loop, review-and-fix) drop `--capture-stdout` from the `RUN_EXTERNAL_AGENT_SH` invocation and add explicit shell `>"$events" 2>"$wrapper"` redirection.
8. **Token ledger raw labels use UNDERSCORES**: `codex_review_fix`, `codex_lint_fix`, `codex_negotiation` — never the hyphen form for the raw bucket label argument. No additions to `scripts/lib-timing-kinds.sh` (per FINDING_8 — telemetry pathway is token-ledger only).
9. **Existing `*.events.jsonl` exclusion in `scripts/larch-log.sh` is UNCHANGED**: Item B does NOT add events.jsonl files to `round_artifact_included` (FINDING_14 security: events.jsonl files contain prompts/responses/repo content; staying excluded keeps content out of committed public run-logs). `SECURITY.md` adds a paragraph documenting the distinction.
10. **Item C strict**: only `scout-archetype-yield.tsv` is added to the include alternation at `scripts/larch-log.sh:89`. No broader sweep.
11. **Cursor fallback paths UNCHANGED**: at all 3 Item B sites, the Cursor branches/calls are byte-identical to pre-PR state (Round 1 Decision 7 non-goal).
12. **No `set -e` change in `get-issue-state.sh`**: `set -uo pipefail` remains; do NOT switch to `-euo pipefail` (Round 1 Decision 6).
13. **`check-reviewers.sh` UNCHANGED**: explicitly out of scope (Round 1 Q1).
14. **Sibling `.md` siblings updated in same PR** for every modified production script (5 scripts → 5 sibling .md files updated). Per the `.claude/rules/script-md-siblings.md` rule.
15. **CI passes**: `bash scripts/relevant-checks.sh` and `make lint` clean before merge.

diff_lines: 400
