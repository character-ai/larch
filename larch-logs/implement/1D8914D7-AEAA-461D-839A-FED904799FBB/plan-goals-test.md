## Goal
Consolidate /implement Step 7a body (diagram, comment composition, rebase, pre-bump log flush) into a single foreground orchestration helper at skills/implement/scripts/step-7a.sh, preserving byte-identical larch:diagrams output.

## Implementation Plan
## Plan

# Implementation Plan — Consolidate /implement Step 7a body into skills/implement/scripts/step-7a.sh (issue #2741)

## Files to modify/create

### NEW: `skills/implement/scripts/step-7a.sh`

Single foreground orchestration helper that absorbs the entire current Step 7a body. Phases (executed in this exact order to preserve byte-identical output):

1. **Bootstrap**: `set -uo pipefail` (not `-e` — most child helper failures are non-fatal warnings, not script-killing exits; `flush-execution-issues.sh` and most `larch-log.sh write` calls trail with `|| append-tool-failure.sh` or `|| true`). `source "$PLUGIN_ROOT/scripts/lib-quiet.sh"`, `larch_quiet_init`. Argv: `--implement-tmpdir PATH [--issue-number N] [--run-id ID] [--no-logs-commit BOOL] [--forked-target BOOL]`. `usage()` and `fail_usage()` mirror `flush-execution-issues.sh` (argv error → exit 2 with `STEP_7A_BAIL_REASON=argv`). All non-argv child failures continue and emit warnings; only argv errors / missing required `--implement-tmpdir` bail early.
2. **Session rehydration**: When environment is missing `CLAUDE_PLUGIN_ROOT`, `LARCH_TOKEN_SESSION_ID`, `LARCH_CLAUDE_SOURCE_FILE`, or `LARCH_TIMING_LEDGER`, recover from `$IMPLEMENT_TMPDIR/session-env.sh` via `read-session-env-key.sh` (one call per key). When `--issue-number` / `--run-id` / `--no-logs-commit` / `--forked-target` are absent on argv, fall back to their `read-session-env-key.sh` values (keys: `LARCH_ISSUE_NUMBER`, `LARCH_RUN_ID`, `LARCH_NO_LOGS_COMMIT`, `LARCH_FORKED_TARGET`) with the same defaults today's SKILL.md uses.
3. **Token/timing marks for Step 7a**: `token-ledger.sh mark "Step 7a — code flow diagram"` and `timing-ledger.sh mark "Step 7a — code flow diagram"` (best-effort).
4. **Small/non-runtime classifier**: replicate the current SKILL.md detector exactly. `MERGE_BASE=$(git merge-base HEAD origin/main 2>/dev/null) || MERGE_BASE=""`. When `MERGE_BASE` is non-empty: `CHANGED_FILES=$(git diff --name-only "${MERGE_BASE}..HEAD" 2>/dev/null)`, `CHANGED_COUNT=$(printf '%s\n' "$CHANGED_FILES" | grep -c . 2>/dev/null || echo 0)`. Treat as inconclusive (proceed with full generation) when `MERGE_BASE` is empty OR `CHANGED_COUNT` is 0. Otherwise classify as small/non-runtime when `CHANGED_COUNT` is 1 or 2 AND every path resides under `docs/`, OR is named `CHANGELOG`/`CHANGELOG.md`, OR has extension `.txt`/`.tsv` — with the same caveat that `.md` outside `docs/` does NOT qualify.
5. **Diagram phase**:
   - **Skip path** (small/non-runtime classifier fired): set `DIAGRAM_STATUS=skip`, `DIAGRAM_PATH=""`, `CODE_FLOW_SKIP_REASON="(Code Flow Diagram skipped — small/non-runtime change)"`. Print `⏩ 7a: diagrams status=skip reason=small-non-runtime-change elapsed=<elapsed>`. Proceed to comment composition (still posts with placeholder).
   - **Generate path**: invoke `generate-code-flow-diagram.sh --implement-tmpdir "$IMPLEMENT_TMPDIR"`. Parse its `STATUS=ok|skipped|failed` and `SKIP_REASON` from stdout via `awk` (Bash 3.2 compatible). Map to `DIAGRAM_STATUS=ok|skipped|failed` accordingly. On `STATUS=ok`, set `DIAGRAM_PATH=$IMPLEMENT_TMPDIR/code-flow-diagram.md`, `CODE_FLOW_SKIP_REASON=""`. On `STATUS=skipped`, set `DIAGRAM_PATH=""`, `CODE_FLOW_SKIP_REASON="Code flow diagram not available."`. On `STATUS=failed`, set `DIAGRAM_PATH=""`, `CODE_FLOW_SKIP_REASON="Code flow diagram not available."`, append a `Step 7a — generate-code-flow-diagram failed: <captured stderr>` entry under `Warnings` in `$IMPLEMENT_TMPDIR/execution-issues.md` via `append-tool-failure.sh`.
6. **Comment composition**: compose `$IMPLEMENT_TMPDIR/summary-diagrams.md` via Bash file operations (NOT Read/Write tools — keep content out of orchestrator context). Architecture diagram: when `$ARCHITECTURE_DIAGRAM_FILE` is non-empty and the file exists, `cat` it; else `printf 'Architecture diagram not available.'`. Then `printf '\n\n'`. Code Flow: when `$IMPLEMENT_TMPDIR/code-flow-diagram.md` exists, `cat` it; else `printf '%s' "$CODE_FLOW_SKIP_REASON"`. Mirror SKILL.md lines 1401-1416 byte-for-byte.
7. **larch:diagrams summary comment upsert**: when `[ -n "$ISSUE_NUMBER" ]`, run `tracking-issue-summary.sh upsert-summary --issue "$ISSUE_NUMBER" --marker "<!-- larch:diagrams v1 runid=$RUN_ID -->" --content-file "$IMPLEMENT_TMPDIR/summary-diagrams.md"`. Capture stdout via command substitution to extract the `COMMENT_URL=<url>` line; set local `COMMENT_URL` from that match (empty when not found). On non-zero exit, append `Step 7a — larch:diagrams upsert failed` to `Tool Failures` in `execution-issues.md` via `append-tool-failure.sh`, set `COMMENT_URL=""`, continue. Sanitizer rejection still upserts the placeholder body; only empty `ISSUE_NUMBER` gates the comment.
9. **rebase-checkpoint-probe.sh 7a.r**: build `BASE_ARGS=()`; when `[ "${forked_target:-false}" = "true" ]`, append `--base-remote upstream --base-ref main`. Run `export LARCH_QUIET_BREADCRUMBS=1` (matches today's SKILL.md), then `"$PLUGIN_ROOT/scripts/rebase-checkpoint-probe.sh" 7a.r 'diagrams' "${BASE_ARGS[@]+"${BASE_ARGS[@]}"}"`. Do NOT capture its exit into a bail variable — the existing Rebase Checkpoint Macro orchestrator routing is documented in `## Rebase Checkpoint Macro` and is owned by the caller (SKILL.md prose after step-7a.sh returns). step-7a.sh is the helper, not the macro router; it must propagate the probe's KV envelope on FD 3 (`emit` lines from the probe pass through naturally because lib-quiet's FD 3 is inherited).
10. **Pre-bump log flush** — exactly matches SKILL.md lines 1457-1527:
    1. `token-ledger.sh mark "Step 8 — version bump"` (best-effort)
    2. `timing-ledger.sh mark "Step 8 — version bump"` (best-effort)
    3. `flush-execution-issues.sh --issue-log "$IMPLEMENT_TMPDIR/execution-issues.md" --log-root "$IMPLEMENT_TMPDIR/larch-logs" --run-id "$RUN_ID" 2>"$IMPLEMENT_TMPDIR/pre-bump-flush-execution-issues.log"` with `|| append-tool-failure.sh ...` fallback (site `step-7a`, category `Tool Failures`).
    4. `token-report.sh --full --format json --output "$IMPLEMENT_TMPDIR/token-report-rendered.json" || true`
    5. `timing-report.sh --full --format json --output "$IMPLEMENT_TMPDIR/timing-report-rendered.json" || true`
    6. `larch-log.sh write` for batches: `token-report`, `timing-report` (unconditional), plus conditional file-existence checks for `parent-issue`, `pre-review-head`, `pre-review-untracked`, `codex-impl-transcript`, `codex-impl-transcript-meta` (uses `lib-redact.sh` `larch_redact_strip_meta_cmd_json`), `codex-impl-transcript-prompt`, `codex-commit-message`, `codex-impl-manifest-raw`. All `|| true`.
    7. `capture-session-transcript.sh --source-file "$LARCH_CLAUDE_SOURCE_FILE" --log-root "$IMPLEMENT_TMPDIR/larch-logs" --skill implement --run-id "$RUN_ID" --no-logs-commit "${no_logs_commit:-false}" --defer-commit "true" --execution-issues-log "$IMPLEMENT_TMPDIR/execution-issues.md"` — always exits 0; emits `SESSION_TRANSCRIPT_STATUS=...` to its own stdout (suppress with `>/dev/null` to match `refresh-run-logs.sh` retry-path semantics; main path matches SKILL.md which leaves stdout visible — preserve current behavior, capture but do not act on the status line).
    8. `flush-execution-issues.sh --step-label 7a-post-transcript --source-label "execution-issues.md post-transcript refresh" ...` (post-transcript refresh) with `|| append-tool-failure.sh ...` fallback.
    9. When `[ "${no_logs_commit:-false}" != "true" ]`: `larch-log.sh commit --log-root "$IMPLEMENT_TMPDIR/larch-logs" --skill implement --run-id "$RUN_ID" || true`.

    Aggregate `LOG_FLUSH_STATUS=ok` when no helper non-zero exit recorded; `LOG_FLUSH_STATUS=degraded` when any of `flush-execution-issues.sh`, `capture-session-transcript.sh`, or `larch-log.sh commit` failed (other batches' `larch-log.sh write` failures do not flip the status to degraded — they are write-best-effort per current SKILL.md, but failures still log to `Tool Failures` via `append-tool-failure.sh`). `LOG_FLUSH_STATUS=skipped-no-logs-commit` when `no_logs_commit=true` AND the commit step was skipped.
11. **Final KV tail** via `emit_kv` on FD 3:
    - `DIAGRAM_STATUS=ok|skipped|failed|skip` (skip = small/non-runtime classifier; the four enum strings match the issue acceptance and current SKILL.md semantics).
    - `DIAGRAM_PATH=<path-or-empty>` (matches `generate-code-flow-diagram.sh` output convention).
    - `COMMENT_URL=<url-or-empty>` (extracted from `tracking-issue-summary.sh` stdout; empty when ISSUE_NUMBER empty OR upsert skipped OR upsert failed).
    - `LOG_FLUSH_STATUS=ok|degraded|skipped-no-logs-commit`.
    - `STEP_7A_BAIL_REASON=<reason-or-empty>` — empty on the happy path; on argv error, set to `argv` before the `exit 2`. step-7a.sh does NOT set a bail reason for diagram/comment/flush degradation (those are warnings, not bails).
12. **Exit propagation**: argv errors exit `2`. Rebase failures preserve the wrapper exit on the step-7a.sh process itself: conflict exits `1`, non-conflict failure exits `3`, and other non-zero probe exits are relayed unchanged. On all of those non-zero rebase paths, set `LOG_FLUSH_STATUS=skipped-rebase-checkpoint`, emit the diagram KV tail, and skip the pre-bump flush. Only argv validation sets `STEP_7A_BAIL_REASON=argv`.

### NEW: `skills/implement/scripts/step-7a.md`

Sibling documentation following the `flush-execution-issues.md` / `generate-code-flow-diagram.md` template. Sections:
- Title + 1-paragraph description
- `## Interface` — argv grammar with required/optional flags
- `## Stdout contract` — table of KV keys and value enums (`DIAGRAM_STATUS`, `DIAGRAM_PATH`, `COMMENT_URL`, `LOG_FLUSH_STATUS`, `STEP_7A_BAIL_REASON`)
- `## Exit codes` — `0` happy path / `2` argv error
- `## Bail reasons` — currently only `argv` (extensible if future revisions add bail paths; document explicitly that diagram/comment/flush degradation does NOT bail)
- `## Invariants` — same-order phases as SKILL.md today; preserves byte-identical `larch:diagrams` comment content; preserves `[ -n "$ISSUE_NUMBER" ]` empty-gate; preserves `LARCH_QUIET_BREADCRUMBS=1` during rebase
- `## Edit-in-sync` — name `skills/implement/SKILL.md` Step 7a section and `skills/implement/scripts/test-step-7a.sh`

### NEW: `skills/implement/scripts/test-step-7a.sh`

Offline regression harness following the `test-flush-execution-issues.sh` / `test-step-8a-changelog.sh` template:

- `set -euo pipefail`, `export LARCH_QUIET_DISABLE=1`, `mktemp -d` for `$TMP_ROOT`, `trap 'rm -rf "$TMP_ROOT"' EXIT`.
- Stub plugin tree under `$TMP_ROOT/plugin`: `cp` real `lib-quiet.sh`, `lib-execution-issues.sh`, `lib-redact.sh`; write stub `generate-code-flow-diagram.sh`, `tracking-issue-summary.sh`, `rebase-checkpoint-probe.sh`, `flush-execution-issues.sh`, `capture-session-transcript.sh`, `token-ledger.sh`, `timing-ledger.sh`, `token-report.sh`, `timing-report.sh`, `larch-log.sh`, `read-session-env-key.sh`, `append-tool-failure.sh`. Each stub records its argv to `$TMP_ROOT/calls.log` and emits the expected KV envelope.
- Test cases (acceptance-mandated; each writes a fresh `$IMPLEMENT_TMPDIR`):
  1. `green path`: classifier inconclusive (no merge-base), `generate-code-flow-diagram.sh STATUS=ok`, `tracking-issue-summary.sh` succeeds, all flush helpers succeed. Assert `DIAGRAM_STATUS=ok`, `DIAGRAM_PATH` non-empty, `COMMENT_URL=<stub-url>`, `LOG_FLUSH_STATUS=ok`, `STEP_7A_BAIL_REASON=""`, exit 0. Assert ordering by inspecting `$TMP_ROOT/calls.log` — generate before compose, compose before upsert, upsert before rebase, rebase before flush.
  2. `diagram-skip` (small/non-runtime): construct a 1-file diff matching `docs/X.md`; assert `DIAGRAM_STATUS=skip`, the `⏩ 7a: diagrams status=skip reason=small-non-runtime-change` line was printed, `generate-code-flow-diagram.sh` was NOT invoked (no entry in `calls.log`), comment IS posted with `(Code Flow Diagram skipped — small/non-runtime change)` substring in `summary-diagrams.md`.
  3. `diagram-rejected` (sanitizer-rejected): stub `generate-code-flow-diagram.sh` to emit `STATUS=skipped`, sanitizer-flavored `SKIP_REASON`, and assert `DIAGRAM_STATUS=skipped`, `tracking-issue-summary.sh` still appears in `calls.log`, `COMMENT_URL` is populated, and `summary-diagrams.md` matches the placeholder body byte-for-byte.
  4. `diagram-generation-failure`: stub `generate-code-flow-diagram.sh` to emit `STATUS=failed`, `SKIP_REASON=helper-error` (NOT sanitizer-rejected). Assert `DIAGRAM_STATUS=failed`, comment IS posted with `Code flow diagram not available.` substring, `COMMENT_URL=<stub-url>`, a Warning entry was appended for the generation failure, exit 0.
  5. `summary-upsert-failure`: stub `tracking-issue-summary.sh` to exit 1. Assert `COMMENT_URL=""`, a `Tool Failures` entry was appended to `execution-issues.md`, all subsequent phases (rebase + flush) still executed, exit 0.
  6. `flush-failure`: stub the first `flush-execution-issues.sh` invocation to exit 1. Assert `LOG_FLUSH_STATUS=degraded`, a `Tool Failures` entry was appended, the post-transcript `flush-execution-issues.sh` STILL ran, the final `larch-log.sh commit` STILL ran, exit 0.
  7. `no-logs-commit honored`: pass `--no-logs-commit true`; assert the final `larch-log.sh commit` did NOT appear in `calls.log`, `LOG_FLUSH_STATUS=skipped-no-logs-commit`, exit 0.
  8. `forked-target rebase argv`: pass `--forked-target true`; assert the `rebase-checkpoint-probe.sh` call in `calls.log` contains `--base-remote upstream --base-ref main`.
  9. `ISSUE_NUMBER empty gate`: pass `--issue-number ""`; assert `tracking-issue-summary.sh` did NOT appear in `calls.log`, `COMMENT_URL=""`, the rest of the pipeline still ran.
  10. `argv error`: invoke without `--implement-tmpdir`; assert exit 2, KV envelope includes `STEP_7A_BAIL_REASON=argv`.

- `finish` summary prints `PASS=<N>` and exits 1 when `FAIL>0`.

### NEW: `skills/implement/scripts/test-step-7a.md`

Sibling documentation enumerating the 10 test cases with one-line descriptions; mirrors `test-flush-execution-issues.md` and `test-step-8a-changelog.md` shape.

### UPDATED: `skills/implement/SKILL.md`

Collapse the Step 7a body sections (lines 1366-1531 of current file: the diagram check, the comment composition, the rebase block, the pre-bump flush block) into ONE foreground Bash invocation block plus the surrounding prose anchors that other parts of SKILL.md cross-reference. The replacement structure:

- Preserve the `## Step 7a — Code Flow Diagram` (or equivalent) header and the `**MANDATORY — READ ENTIRE FILE** before writing larch:diagrams summary comments` line (referenced by other steps).
- Replace the multi-fence body with: a brief description sentence + `**⚠ Foreground required — do NOT set \`run_in_background: true\`.**` banner + one fenced bash block invoking step-7a.sh. The block includes the standard `source ~/.cache/larch/sessions/...` rehydration prelude pattern, the per-anchor `# Foreground required: see BASH_AUTHORING.md §4` comment, and a single invocation line:
  ```bash
  "${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/step-7a.sh" \
    --implement-tmpdir "$IMPLEMENT_TMPDIR" \
    --issue-number "${ISSUE_NUMBER:-}" \
    --run-id "$RUN_ID" \
    --no-logs-commit "${no_logs_commit:-false}" \
    --forked-target "${forked_target:-false}"
  ```
  Parse the KV tail for `DIAGRAM_STATUS`, `DIAGRAM_PATH`, `COMMENT_URL`, `LOG_FLUSH_STATUS`, `STEP_7A_BAIL_REASON` (illustrative; downstream steps don't read these but the macro caller may).
- Preserve the **Rebase Checkpoint Macro orchestrator routing** prose (currently after the rebase fence at line 1453): since rebase-checkpoint-probe.sh is now invoked INSIDE step-7a.sh, the macro routing applies to the propagated KV from step-7a.sh's output. Update the prose to say "after step-7a.sh returns" instead of "after the rebase-checkpoint-probe.sh invocation".
- Preserve the `> **Continue to Step 8 IMMEDIATELY.**` step boundary directive.
- Preserve the "Pre-bump log flush" subsection prose (line 1529-1531) that explains the contract — but the subsection no longer carries its own fence. Replace the fenced block with: "Implemented inside `step-7a.sh` — see `skills/implement/scripts/step-7a.md`. The KV tail's `LOG_FLUSH_STATUS` indicates the aggregate outcome. The orchestrator does not parse this KV — it relies on the in-script `append-tool-failure.sh` callbacks for Tool Failures logging."

Update line 1392 (S030 path pin in `lint-skill-invocations.sh`): retain the literal `${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/generate-code-flow-diagram.sh` reference inside step-7a.sh, but verify the SKILL.md surface no longer contains the literal call (lint-skill-invocations.sh may require an exception entry — check during implementation).

### UPDATED: `scripts/lint-foreground-markers.sh`

Add `step-7a.sh` to the DENYLIST heredoc (currently 12 entries at lines 18-31). The heredoc is alphabetically-leaning but not strictly sorted; insert `step-7a.sh` in a position consistent with existing order (likely after `step2-implement.sh` and before the rebase entries; final placement is the implementer's call).

### UPDATED: `Makefile`

- Add `test-step-7a` to the master `.PHONY` declaration (line 4).
- Add `test-step-7a` to a `test-harnesses-N` shard. Recommend **shard-18** (currently 11 entries — lowest load) for balance; implementer may pick a different shard if a more-related grouping exists.
- Add the target definition near other Step 7a / `flush-execution-issues` targets:
  ```makefile
  test-step-7a:
  	bash scripts/harness-timer.sh $@ bash skills/implement/scripts/test-step-7a.sh
  ```
  Place this definition adjacent to `test-flush-execution-issues` (lines around 525-530) for code locality.

### UPDATED: `docs/linting.md`

Add one inventory row to the harness-table section (near `test-flush-execution-issues` documented at line 258):
- `| `make test-step-7a` | Run the offline regression harness for `/implement` Step 7a's consolidated body helper `step-7a.sh`. Covers the green path (diagram + comment + rebase + flush), diagram-skip (small/non-runtime classifier), diagram-rejected (sanitizer skip-upsert), diagram-generation-failure, summary-upsert failure, flush failure, no-logs-commit honoring, forked-target rebase argv, ISSUE_NUMBER empty gate, and argv error. A `make lint` prerequisite via the `test-harnesses-N` shard partition. |`

## Approach

step-7a.sh is a **call-and-emit orchestration wrapper**. It does no logic of its own beyond classifier evaluation, argv parsing, KV aggregation, and `append-tool-failure.sh` routing on non-zero child exits. Every behavior visible today in SKILL.md Step 7a lines 1366-1531 is preserved byte-for-byte:

- Classifier: same `MERGE_BASE` / `CHANGED_COUNT` evaluation + same path-eligibility ruleset.
- Diagram generation: delegated to `generate-code-flow-diagram.sh` unchanged.
- Summary comment composition: composed via Bash `cat`/`printf` to `summary-diagrams.md`, then posted via `tracking-issue-summary.sh upsert-summary`. The `[ -n "$ISSUE_NUMBER" ]` empty-gate and sanitizer-rejection skip are honored.
- Rebase 7a.r: `rebase-checkpoint-probe.sh 7a.r 'diagrams' [--base-remote upstream --base-ref main]` with `LARCH_QUIET_BREADCRUMBS=1` exported.
- Pre-bump flush: same `flush-execution-issues.sh`, `token-report.sh`, `timing-report.sh`, multi-batch `larch-log.sh write`, `capture-session-transcript.sh`, post-transcript `flush-execution-issues.sh`, and conditional `larch-log.sh commit`.

The helper makes ONE simplification: it does not add a `diagrams` larch-log batch (the issue Goal item #3 is reinterpreted as "compose `summary-diagrams.md`", since SKILL.md:1418 explicitly says "Do NOT write a `diagrams` larch-log batch" and `larch-log-batches.sh` has no `diagrams` slug). Byte-identical mirroring REQUIRES not adding such a batch.

Per Round 1 Decision 1, rebase-checkpoint-probe.sh 7a.r runs INSIDE step-7a.sh between the comment upsert and the pre-bump flush — matching today's execution order exactly. The macro orchestrator routing (separately documented in SKILL.md `## Rebase Checkpoint Macro`) consumes the propagated KV via FD 3 inheritance.

Per Round 1 Decision 2, the comment-upsert skip rule mirrors today's SKILL.md byte-for-byte: comment is posted with placeholders on generation failure/skip; ONLY skipped when the Mermaid sanitizer emits a rejection token in `SKIP_REASON`; the `ISSUE_NUMBER` empty-gate is preserved.

Per Round 1 Decision 3, the flush phase absorbs ALL current pre-bump batches — not just the 4 listed in the issue Goal.

## Edge cases

1. **Sanitizer-rejection signal**: `generate-code-flow-diagram.sh`'s `SKIP_REASON` field on `STATUS=failed` must distinguish sanitizer rejection from other failure modes. Implementation must read the SKIP_REASON value and substring-match the sanitizer's REASON_TOKEN convention (verified during implementation against `sanitize-mermaid-fragment.sh` reject paths). When the token taxonomy is ambiguous, prefer the conservative interpretation: treat any `STATUS=failed` with `SKIP_REASON` containing `reject` / `rejected` / `sanitiz` as sanitizer rejection.
2. **`ARCHITECTURE_DIAGRAM_FILE` empty/missing**: today's SKILL.md (lines 1404-1408) checks `[ -n "${ARCHITECTURE_DIAGRAM_FILE:-}" ] && [ -f "${ARCHITECTURE_DIAGRAM_FILE:-}" ]` before `cat`-ing it; falls back to `printf 'Architecture diagram not available.'`. step-7a.sh preserves this exact gate. The variable is set by the upstream `/design` flow or by the implementation step's architecture pass; step-7a.sh reads it from environment.
3. **`forked_target=true` rebase argv**: when forked-target mode is active, the `BASE_ARGS` array MUST be expanded with `"${BASE_ARGS[@]+"${BASE_ARGS[@]}"}"` (Bash 3.2 safe expansion under `set -u`); a naive `"${BASE_ARGS[@]}"` would trigger "unbound variable" when the array is empty.
4. **`no_logs_commit=true`**: skips the FINAL `larch-log.sh commit` but does NOT skip the prior `larch-log.sh write` calls (preserves today's SKILL.md line 1524 conditional shape).
5. **`capture-session-transcript.sh` stdout**: the helper always exits 0 and emits `SESSION_TRANSCRIPT_STATUS=<status>` to stdout. Today's SKILL.md leaves this visible. step-7a.sh preserves visibility (does NOT redirect stdout away). The `--execution-issues-log` argv ensures the wrapper appends its own warning entry to `execution-issues.md` regardless, so the post-transcript `flush-execution-issues.sh` carries any non-OK status into the NDJSON batch.
6. **KV propagation from `rebase-checkpoint-probe.sh`**: the probe emits its own `emit` lines on FD 3 (via lib-quiet's contract). step-7a.sh inherits FD 3 from its caller, so the probe's KV passes through to the orchestrator naturally without re-emission. step-7a.sh's own `emit_kv` calls append to the same stream; ordering matters (probe's lines appear before step-7a.sh's final tail in stream order).
7. **Bash 3.2 array safety**: all array constructions (`BASE_ARGS=()`) MUST use the `"${arr[@]+"${arr[@]}"}"` expansion pattern under `set -u` to survive empty-array expansion. No `declare -A`, no `mapfile`, no `${var^^}`, no `&>>`.

## Failure modes

1. **`generate-code-flow-diagram.sh` non-zero exit (not `STATUS=failed` envelope)**: indicates a crash before lib-quiet emit completed. step-7a.sh treats this identically to `STATUS=failed` (set placeholder, post comment, continue). Earliest warning signal: the captured stderr file is non-empty AND no `STATUS=` line in captured stdout. Mitigation: stub `generate-code-flow-diagram.sh` in the test harness to exit 99 with empty stdout; assert step-7a.sh still proceeds.
2. **`tracking-issue-summary.sh upsert-summary` API rate-limit / network failure**: returns non-zero; step-7a.sh appends a `Tool Failures` entry and continues (does NOT bail). Earliest warning signal: `COMMENT_URL=""` in step-7a.sh's emitted KV tail. Mitigation: orchestrator-level retry happens elsewhere (Step 18 safety net, run-log refresh paths); step-7a.sh stays best-effort.
3. **`larch-log.sh commit` failure during rebase race**: another concurrent commit on the branch causes `git commit` inside `larch-log.sh commit` to fail. step-7a.sh appends `Tool Failures` and continues. The branch is then in an inconsistent state where flush-batch files exist as staged-but-uncommitted; Step 18 (teardown safety net) cleans this up. Earliest warning signal: a non-fatal `git: ` line in `pre-bump-flush-execution-issues.log` and `LOG_FLUSH_STATUS=degraded`. Mitigation: rely on Step 18 + refresh-run-logs.sh retry paths (out of step-7a.sh scope).

## Testing strategy

The offline harness `test-step-7a.sh` is the primary verification surface. It MUST cover all 6 acceptance-listed test cases plus 4 additional cases (no_logs_commit honored, forked-target argv, ISSUE_NUMBER empty gate, argv error) — 10 cases total. Each test:

- Builds a fresh stub plugin tree with `cp` for real libs (`lib-quiet.sh`, `lib-execution-issues.sh`, `lib-redact.sh`) and write-via-heredoc for stubbed scripts.
- Each stubbed script appends its argv + cwd to `$TMP_ROOT/calls.log` (newline-delimited; Bash 3.2 safe) and emits a deterministic KV envelope on FD 3.
- The harness asserts: exit code, ordering of `calls.log` entries (via `grep -n`), KV output content (via `grep -F` on the captured stdout), `execution-issues.md` content (via `cat` + `grep`).

CI integration: `make test-step-7a` is wired into a `test-harnesses-N` shard (recommend shard-18). The harness fails closed when any assertion fails; PASS=10 indicates all green.

Manual verification on a live `/implement` run after landing: a transcript review should show ~1 Bash call in Step 7a section body (down from ~5 today, before companion-issue rebase consolidation). The `larch:diagrams` comment on the tracking issue should be byte-identical to a pre-change baseline (diff the comment content from a recent merged PR's tracking issue against the post-change run's tracking issue).



## Acceptance

- `skills/implement/scripts/step-7a.sh` exists and absorbs the Step 7a body phases: rehydrate env, token/timing marks, small/non-runtime classifier, `generate-code-flow-diagram.sh`, compose `summary-diagrams.md`, `tracking-issue-summary.sh upsert-summary --marker larch:diagrams` (gated only on non-empty `ISSUE_NUMBER`), `rebase-checkpoint-probe.sh 7a.r diagrams`, full pre-bump log flush (`flush-execution-issues.sh` pre- and post-transcript, `token-report.sh`, `timing-report.sh`, multi-batch `larch-log.sh write`, `capture-session-transcript.sh`, conditional `larch-log.sh commit`), and a final `emit_kv` tail.
- Sibling `skills/implement/scripts/step-7a.md` documents argv, output KV grammar (`DIAGRAM_PATH`, `DIAGRAM_STATUS`, `COMMENT_URL`, `LOG_FLUSH_STATUS`, `STEP_7A_BAIL_REASON`), exit codes (0 happy / 2 argv), and bail reasons.
- `skills/implement/scripts/test-step-7a.sh` offline harness covers: green path, diagram-skip (small/non-runtime), diagram-rejected (sanitizer placeholder upsert), diagram-generation-failure, summary-upsert failure, flush failure, `no-logs-commit` honoring, forked-target rebase argv, empty `ISSUE_NUMBER` gate, unexpected rebase rc propagation, and argv error.
- `skills/implement/SKILL.md` Step 7a section collapses to one foreground Bash invocation block (banner + per-anchor comment per BASH_AUTHORING.md §4); the surrounding Rebase Checkpoint Macro routing prose still applies via step-7a.sh propagated KV.
- `scripts/lint-foreground-markers.sh` DENYLIST includes `step-7a.sh`.
- `Makefile` registers `test-step-7a` (target + `.PHONY` + a `test-harnesses-N` shard); `docs/linting.md` documents the harness in the inventory.
- `make lint` passes (lint-bash32, script-md-siblings, lint-foreground-markers, lint-skill-invocations).
- `larch:diagrams` summary comment on the tracking issue is byte-identical to current SKILL.md output (Architecture Diagram + Code Flow Diagram OR placeholder; sanitizer rejection still upserts the placeholder body; `ISSUE_NUMBER` empty gate preserved).
- A live `/implement <issue>` run transcript shows ~1 Bash call for the Step 7a body (down from ~5 today).
- step-7a.sh does NOT write a `diagrams` larch-log batch (no such slug exists in `scripts/larch-log-batches.sh`; SKILL.md:1418 explicitly forbids it).

diff_lines: 845

## Test plan
(no test plan section in plan-file)
