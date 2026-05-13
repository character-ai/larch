---
name: review
description: "Use when reviewing code changes (--diff for branch diff, or positional text for existing code review). Description mode files findings as issues by default (--no-issues suppresses)."
argument-hint: "[--diff] [--subagent] [--no-issues] [--session-env <path>] [--step-prefix <prefix>] [<description>]"
allowed-tools: AskUserQuestion, Bash, Read, Edit, Write, Grep, Glob, Agent, Task, WebFetch, Skill
---

# Code Review Skill

Review code changes with a specialist panel and a scripted collection/voting pipeline. Diff mode (`--diff`) reviews the current branch against `main`, applies accepted fixes, and repeats until convergence or the round cap. Description mode reviews a resolved file set, is read-only, and files accepted findings as issues unless `--no-issues` is set.

**Anti-halt continuation reminder.** After every child `Skill` tool call (e.g., `/design`, `/review`, `/bump-version`, `/issue`, `/implement`) returns AND after every `Bash` tool call that completes a numbered step or sub-step, including `run-relevant-checks-captured.sh`, IMMEDIATELY continue with this skill's NEXT numbered step — do NOT end the turn on the child's cleanup output, on a Bash result, or on a status message, and do NOT write a summary, handoff, status recap, or "returning to parent" message — those are halts in disguise. This applies to ALL step boundaries from Step 0 through Step 5, and to ALL sub-step transitions within Step 3's review loop (3a→3b→3c→3d→3e→3f→loop back to Step 1). **Critical: in diff mode, the review loop (Steps 1→2→3) repeats until convergence (0 findings, or Step 3f classifies the just-fixed round as non-substantial — a main-agent classification of accepted-and-fixed work, not a reading of reviewer prose) or the 3-round safety limit — completing one round's substantial fixes does NOT mean the review is done.** → shared/subskill-invocation.md#anti-halt

**Continue after child returns.** Treat every script and child-skill result as input to the next step, not as a stopping point.

## Flags

Parse flags from `$ARGUMENTS`. Flags may appear in any order; stop at the first non-flag token. After stripping all flags, the remainder (joined as a single string) is the **positional description**. **All flags MUST appear before the positional description.**

- `--diff`: sets `diff_mode=true`; mutually exclusive with positional description text.
- `--no-issues`: suppresses issue filing in description mode; ignored in diff mode.
- `--session-env <path>`: caller-provided session env file.
- `--step-prefix <prefix>`: breadcrumb prefix using the shared progress-reporting encoding.
- `--subagent`: in diff mode, may dispatch Steps 1-3 to `references/heavy-worker.md`.
- `--run-id <ID>`: optional run identifier for review log batches.

Mode activation is fail-closed:

1. If `--diff` present AND positional description text present → **ERROR**: print `**⚠ --diff cannot be combined with a description. Use --diff alone for branch diff review, or provide a description without --diff. Aborting.**` and exit.
2. If `--diff` present → diff mode.
3. If positional description text present → description mode.
4. If neither is present → **ERROR**: print `**⚠ /review requires either --diff (branch diff review) or a description of what to review. Examples: /review --diff, /review implementation of auth module, /review --no-issues error handling in scripts/. Aborting.**` and exit.

## Progress

Read `${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/step-name-registry.tsv` at session start. Print breadcrumb start lines for standalone runs, and suppress parent-visible prose when `SESSION_ENV_PATH` is non-empty. Reviewer prompts preserve the focus-area enum `code-quality / risk-integration / correctness / architecture / security`. Specialist prompts are rendered through `${CLAUDE_PLUGIN_ROOT}/scripts/render-specialist-prompt.sh`.

Script contracts and harnesses: `${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/gather-context.md` / `test-gather-context.sh` / `test-gather-context.md`, `${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/dispatch-panel.md` / `test-dispatch-panel.sh` / `test-dispatch-panel.md`, `${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/collect-findings.md` / `test-collect-findings.sh` / `test-collect-findings.md`, `${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/tally-votes.md` / `test-tally-votes.sh` / `test-tally-votes.md`, `${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/detect-wholesale-rejection.md` / `test-detect-wholesale-rejection.sh` / `test-detect-wholesale-rejection.md`, `${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/emit-tally.md` / `test-emit-tally.sh` / `test-emit-tally.md`, `${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/log-phase.md` / `test-log-phase.sh` / `test-log-phase.md`, and `${CLAUDE_PLUGIN_ROOT}/scripts/launch-claude-subprocess.md` / `test-launch-claude-subprocess.sh` / `test-launch-claude-subprocess.md`.

## Step 0 — Session Setup

Run:

```bash
SESSION_ENV_PATH="$SESSION_ENV_PATH" LARCH_TIMING_SKILL=review "${CLAUDE_PLUGIN_ROOT}/scripts/timing-ledger.sh" mark "review Step 0 — session setup" || true
${CLAUDE_PLUGIN_ROOT}/scripts/session-setup.sh --prefix claude-review --skip-preflight --skip-branch-check --skip-repo-check --check-reviewers [--caller-env "$SESSION_ENV_PATH"] [--skip-codex-probe] [--skip-cursor-probe] [--write-health "${SESSION_ENV_PATH}.health"]
```

Parse `SESSION_TMPDIR`, reviewer health, token session fields, and set `REVIEW_TMPDIR=$SESSION_TMPDIR`. If `SESSION_ENV_PATH` is non-empty, rehydrate `LARCH_TOKEN_SESSION_ID` and `LARCH_CLAUDE_SOURCE_FILE` with `read-session-env-key.sh`.

If `subagent_mode=true` AND `diff_mode=true`, **MANDATORY — READ ENTIRE FILE** before dispatching: `${CLAUDE_PLUGIN_ROOT}/skills/review/references/heavy-worker.md`. If the worker returns `REVIEW_HEAVY=complete`, validate `$REVIEW_TMPDIR/review-summary.json` and proceed to Step 4. If it fails or omits the sentinel, fall back inline at Step 1.

## Step 1 — Gather Context

Run:

```bash
SESSION_ENV_PATH="$SESSION_ENV_PATH" LARCH_TIMING_SKILL=review "${CLAUDE_PLUGIN_ROOT}/scripts/timing-ledger.sh" mark "review Step 1 — gather context" || true
${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/gather-context.sh --mode <diff|description> --output-dir "$REVIEW_TMPDIR" [--description-text "$DESCRIPTION_TEXT" --scope-files "$REVIEW_TMPDIR/scope-files.txt"]
```

Parse `DIFF_FILE`, `FILE_LIST_FILE`, `COMMIT_LOG_FILE`, `COMMIT_COUNT`, `SCOPE_FILES_COUNT`, and `MODE` using safe key readers. In description mode, `SCOPE_FILES_COUNT=0` means print `**⚠ Description resolved to zero files. Nothing to review. Exiting.**`, emit the `### review-result` footer, and proceed to Step 5.

When nested under `/implement`, read `PLAN_FILE` and `FEATURE_FILE` from `SESSION_ENV_PATH` for correctness-specialist plan verification.

## Step 2 — Launch Reviewer Panel

Run:

```bash
SESSION_ENV_PATH="$SESSION_ENV_PATH" LARCH_TIMING_SKILL=review "${CLAUDE_PLUGIN_ROOT}/scripts/timing-ledger.sh" mark "review Step 2 — reviewer panel" || true
${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/dispatch-panel.sh --mode "$MODE" --diff-file "$DIFF_FILE" --commit-count "$COMMIT_COUNT" --scope-files "$FILE_LIST_FILE" --review-tmpdir "$REVIEW_TMPDIR" --codex-available "$codex_available" --cursor-available "$cursor_available" --competition-notice-file "$REVIEW_TMPDIR/competition-notice.md" --plan-file "$PLAN_FILE" --feature-file "$FEATURE_FILE" --description-text "$DESCRIPTION_TEXT" --timing-task-prefix "review-round${round_num}" --launch-claude-subprocess "${CLAUDE_PLUGIN_ROOT}/scripts/launch-claude-subprocess.sh"
```

Parse `EXTERNAL_OUTPUT_FILES`, `CLAUDE_OUTPUT_FILES`, `PANEL_MODE`, `SLOT_COUNT`, and `DISPATCH_OK`. Both-down path: if `PANEL_MODE=both-down`, print `**⚠ Both Cursor and Codex unavailable. Proceeding with 1 Claude generic reviewer. Voting will be skipped (insufficient reviewers).**`

## Step 3 — Review Cycle

**MANDATORY — READ ENTIRE FILE** before executing Step 3: `${CLAUDE_PLUGIN_ROOT}/skills/review/references/domain-rules.md`.

Diff mode repeats Step 3 until no findings, wholesale rejection, non-substantial re-review classification, or the 3-round cap. Description mode runs one round and skips fix implementation.

### 3a — Collect Findings

Run:

```bash
${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/collect-findings.sh --external-output-files <paths...> --claude-output-files <paths...> --mode "$MODE" --timeout 1860 --session-env-path "$SESSION_ENV_PATH" --findings-file "$REVIEW_TMPDIR/findings.md" --oos-file "$REVIEW_TMPDIR/oos.md"
```

Anchor: `collect-agent-results.sh --timeout 1860 --substantive-validation --validation-mode` lives in `collect-findings.sh`.

If `FINDINGS_COUNT=0`, skip to Step 4. If dirty sidecars were detected, aggregate `review-dirty-tree-summary.env`, discard reviewer-introduced changes, and continue.

### 3b — Vote

For rounds 1-3, **MANDATORY — READ ENTIRE FILE** before normal voting: `${CLAUDE_PLUGIN_ROOT}/skills/review/references/voting.md`. If `PANEL_MODE=both-down`, Do NOT load `${CLAUDE_PLUGIN_ROOT}/skills/review/references/voting.md` for voting mechanics; auto-accept Claude findings in `tally-votes.sh`.

```bash
${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/tally-votes.sh --findings-file "$REVIEW_TMPDIR/findings.md" --cursor-available "$cursor_available" --codex-available "$codex_available" --review-tmpdir "$REVIEW_TMPDIR" --session-env-path "$SESSION_ENV_PATH" --both-down <true|false>
${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/detect-wholesale-rejection.sh --accepted-count "$ACCEPTED_COUNT"
```

Rounds 4+ do NOT load `${CLAUDE_PLUGIN_ROOT}/skills/review/references/voting.md`; apply the cap path and proceed to summary.

### 3c — Emit Tally

```bash
${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/emit-tally.sh --tally-file "$TALLY_FILE" --accepted-findings-file "$ACCEPTED_FINDINGS_FILE" --oos-file "$REVIEW_TMPDIR/oos.md" --review-tmpdir "$REVIEW_TMPDIR" --session-env-path "$SESSION_ENV_PATH" --round "$round_num" --mode "$MODE" --implement-tmpdir "$IMPLEMENT_TMPDIR"
```

`emit-tally.sh` writes `review-round-summary.md`, `review-summary.json`, and `rejected-findings.md`.

### 3d — Implement Fixes

Diff mode only: implement accepted findings with the main agent using Edit/Write. Do not implement OOS findings. Run the relevant-checks captured helper after non-trivial fixes:

```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/run-relevant-checks-captured.sh" --site review-step3d --tmpdir "$REVIEW_TMPDIR"
```

### 3e — Re-review Classification

Classify the just-fixed round as substantial or non-substantial using main-agent judgment. If substantial and under the round cap, loop to Step 1. If non-substantial, no findings, wholesale rejection, description mode, or cap reached, proceed to Step 4.

### 3f — Anti-halt at convergence exit

When exiting the Step 3 loop after a non-substantial classification, treat any printed convergence prose as a status marker only: the non-substantial re-review convergence line is not terminal — continue into Step 4 without ending the turn.

## Step 4 — Final Summary and Issues

### 4c — Emit summaries and footers

Standalone diff mode prints `review-round-summary.md`. Nested mode copies artifacts and emits only the `### review-result` footer. Description mode composes issue pieces, then invokes `/umbrella` via the Skill tool with `--pieces-json` unless `--no-issues` is set, and holds security-tagged findings locally.

**Continue to Step 4d IMMEDIATELY** after the above outputs for the applicable mode — do not end the turn on summaries or umbrella dispatch alone.

### 4d — Run logging and pre-cleanup boundary

If `RUN_ID` is non-empty, write flat review larch-log batches with `log-phase.sh`: `review-context`, `review-panel-manifest`, `review-findings`, `review-tally`, and `review-round-summary`.

The nested-mode `### review-result` machine footer marks artifact handoff only; the review-result footer is not terminal until Step 5 cleanup (or parent-owned tmpdir rules) completes — continue without ending the turn after emitting it.

## Step 5 — Cleanup

Run cleanup unless a parent owns the tmpdir:

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/cleanup-tmpdir.sh "$REVIEW_TMPDIR"
```

End with `✅ review complete` for standalone mode or the machine footer for nested mode.
