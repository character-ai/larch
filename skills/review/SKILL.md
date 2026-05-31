---
name: review
description: "Use when reviewing code changes (--diff for branch diff, or positional text for existing code review). Description mode records accepted OOS items in local artifacts for manual `/issue` follow-up."
argument-hint: "[--diff] [--subagent] [--dynamic-archetypes <N>] [--session-env <path>] [--step-prefix <prefix>] [<description>]"
allowed-tools: AskUserQuestion, Bash, Read, Edit, Write, Grep, Glob, Agent, Task, WebFetch, Skill
---

# Code Review Skill

Thin wrapper around `${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/review-core.sh`. It owns flag parsing, session setup, the outer diff-mode round loop, fix application, final summaries/issues, run logging, and cleanup. `review-core.sh` owns one gather→dispatch→collect→aggregate→vote→emit round (`aggregate-findings.sh` may no-op when disabled, when fewer than two findings are present, or when merge/dispatch/validation fails and leaves `findings.md` unchanged).

**Anti-halt continuation reminder.** After every child `Skill` tool call (e.g., `/design`, `/review`, `/bump-version`, `/issue`, `/implement`) returns AND after every `Bash` tool call that completes a numbered step or sub-step, including `run-relevant-checks-captured.sh`, IMMEDIATELY continue with this skill's NEXT numbered step — do NOT end the turn on the child's cleanup output, on a Bash result, or on a status message, and do NOT write a summary, handoff, status recap, or "returning to parent" message — those are halts in disguise. This applies to ALL step boundaries from Step 0 through Step 5, and to ALL sub-step transitions within Step 3's review loop (3a→3b→3c→3d→3e→3f→loop back to Step 1). **Critical: in diff mode, the review loop (Steps 1→2→3) repeats until convergence (0 findings, or Step 3f classifies the just-fixed round as non-substantial — a main-agent classification of accepted-and-fixed work, not a reading of reviewer prose) or the 3-round safety limit — completing one round's substantial fixes does NOT mean the review is done.** → shared/subskill-invocation.md#anti-halt **Continue after child returns.** Treat every script and child-skill result as input to the next step, not as a stopping point.

Parse flags from `$ARGUMENTS`: `--diff`, `--dynamic-archetypes <N>`, `--session-env <path>`, `--step-prefix <prefix>`, `--subagent`, and `--run-id <ID>`. Flags may appear in any order before the positional description; `--diff` and positional description are the two mode activators and are mutually exclusive. `--dynamic-archetypes` must be `0..8`; when absent, `LARCH_DYNAMIC_ARCHETYPES_MAX` may supply the same range, default `0`.

Mode activation is fail-closed: if `--diff` and positional description are both present, print `**⚠ --diff cannot be combined with a description. Use --diff alone for branch diff review, or provide a description without --diff. Aborting.**` and exit. If neither is present, print `**⚠ /review requires either --diff (branch diff review) or a description of what to review. Examples: /review --diff, /review implementation of auth module, /review error handling in scripts/. Aborting.**` and exit.

Progress and prompt pins: read `step-name-registry.tsv`; reviewer prompts preserve `code-quality / risk-integration / correctness / architecture / security`; specialist prompts are rendered through `${CLAUDE_PLUGIN_ROOT}/scripts/render-specialist-prompt.sh`; description mode preserves the `### In-Scope Findings` / `### Out-of-Scope Observations` dual-list contract hints.

Script contracts and harnesses: `${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/gather-context.sh` / `${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/gather-context.md` / `${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/test-gather-context.sh` / `${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/test-gather-context.md`, `${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/review-core.sh` / `${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/review-core.md` / `${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/test-review-core.sh` / `${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/test-review-core.md`, `${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/dispatch-panel.sh` / `${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/dispatch-panel.md` / `${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/test-dispatch-panel.sh` / `${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/test-dispatch-panel.md`, `${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/collect-findings.sh` / `${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/collect-findings.md` / `${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/test-collect-findings.sh` / `${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/test-collect-findings.md`, `${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/aggregate-findings-phrases.inc.bash` (sourced by `aggregate-findings.sh` for round-relative failure pointers), `${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/aggregate-findings.sh` / `${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/aggregate-findings.md` / `${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/test-aggregate-findings.sh` / `${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/test-aggregate-findings.md`, `${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/tally-code-votes.sh` / `${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/tally-code-votes.md` / `${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/test-tally-code-votes.sh` / `${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/test-tally-code-votes.md`, `${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/test-findings-classification.sh` / `${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/test-findings-classification.md`, `${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/check-reviewer-failure-threshold.sh` / `${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/check-reviewer-failure-threshold.md` / `${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/test-check-reviewer-failure-threshold.sh` / `${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/test-check-reviewer-failure-threshold.md`, `${CLAUDE_PLUGIN_ROOT}/scripts/dispatch-code-voters.sh` / `${CLAUDE_PLUGIN_ROOT}/scripts/dispatch-code-voters.md` / `${CLAUDE_PLUGIN_ROOT}/scripts/test-dispatch-code-voters.sh` / `${CLAUDE_PLUGIN_ROOT}/scripts/test-dispatch-code-voters.md`, `${CLAUDE_PLUGIN_ROOT}/scripts/lib-vote-tally.sh` / `${CLAUDE_PLUGIN_ROOT}/scripts/lib-vote-tally.md` / `${CLAUDE_PLUGIN_ROOT}/scripts/test-lib-vote-tally.sh` / `${CLAUDE_PLUGIN_ROOT}/scripts/test-lib-vote-tally.md`, `${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/emit-tally.sh` / `${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/emit-tally.md` / `${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/test-emit-tally.sh` / `${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/test-emit-tally.md`, `${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/log-phase.sh` / `${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/log-phase.md` / `${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/test-log-phase.sh` / `${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/test-log-phase.md`, and `${CLAUDE_PLUGIN_ROOT}/scripts/launch-claude-subprocess.sh` / `${CLAUDE_PLUGIN_ROOT}/scripts/launch-claude-subprocess.md`, `${CLAUDE_PLUGIN_ROOT}/scripts/dispatch-with-waterfall.sh` / `${CLAUDE_PLUGIN_ROOT}/scripts/dispatch-with-waterfall.md` / `${CLAUDE_PLUGIN_ROOT}/scripts/test-dispatch-with-waterfall.sh`, and `${CLAUDE_PLUGIN_ROOT}/scripts/launch-claude-review.sh` / `${CLAUDE_PLUGIN_ROOT}/scripts/launch-claude-review.md` / `${CLAUDE_PLUGIN_ROOT}/scripts/test-launch-claude-review.sh`.

Dynamic reviewer scout contract and harness: `${CLAUDE_PLUGIN_ROOT}/scripts/scout-dynamic-archetypes.sh` / `${CLAUDE_PLUGIN_ROOT}/scripts/scout-dynamic-archetypes.md` / `${CLAUDE_PLUGIN_ROOT}/scripts/test-scout-dynamic-archetypes.sh`.

<!-- step:0 — Session Setup -->
## Step 0 — Session Setup

Print `> **🔶 /review 0: setup**`. Rehydrate `CLAUDE_PLUGIN_ROOT` from `SESSION_ENV_PATH` when needed, mark timing, then run `${CLAUDE_PLUGIN_ROOT}/scripts/session-setup.sh --prefix claude-review --skip-preflight --skip-branch-check --skip-repo-check --check-reviewers [--caller-env "$SESSION_ENV_PATH"] [--skip-codex-probe] [--skip-cursor-probe]`. Parse `SESSION_TMPDIR`, reviewer presence, token session fields, set `REVIEW_TMPDIR=$SESSION_TMPDIR`, and export the nested timing ledger. If `subagent_mode=true` AND `diff_mode=true`, **MANDATORY — READ ENTIRE FILE** before dispatching: `${CLAUDE_PLUGIN_ROOT}/skills/review/references/heavy-worker.md`; on `REVIEW_HEAVY=complete`, parse and bind any returned `SCOUT_STATUS`, `SCOUT_FAIL_REASON`, `DYNAMIC_SLOTS`, `SCOUT_MANIFEST`, `YIELD_TSV_FILE`, and round-scoped `FINDINGS_CLASSIFICATION_TSV_FILE[_ROUND_<N>]` KVs before Step 4 log-batch work, validate summary artifacts, and proceed to Step 4; otherwise fall back inline.

**Degraded-tools gate (#3207).** After the presence parse above, run the **Degraded-tools gate (Step 0)** procedure in `${CLAUDE_PLUGIN_ROOT}/skills/shared/external-reviewers.md`: invoke `${CLAUDE_PLUGIN_ROOT}/scripts/degraded-tools-gate.sh` with explicit `--codex-binary-found` / `--codex-present` / `--cursor-binary-found` / `--cursor-present` from the session-setup parse in this Step 0 block (do not omit flags and rely on shell exports) and `--skill review`. If `DEGRADED=true` on an **interactive, non-subagent** run: when `BOTH_DOWN` is **exactly** `false` (one tool unavailable), print the explanation block as a notice, write the `.degraded-tools-gate-prompted` sentinel, and proceed; when `BOTH_DOWN` is `true` or empty/unset (both tools unavailable or parse failed), present the explanation block and fire `AskUserQuestion` with **Continue (degraded waterfall)** / **Abort**; on **Abort**, run `${CLAUDE_PLUGIN_ROOT}/scripts/cleanup-tmpdir.sh --dir "$REVIEW_TMPDIR"` and stop. In **`--subagent` mode or any non-interactive run** (a subagent cannot prompt), do not call `AskUserQuestion` — log the explanation and proceed degraded. Guard with a `$REVIEW_TMPDIR/.degraded-tools-gate-prompted` sentinel. The gate does not flip `codex_available` / `cursor_available`; the `dispatch-panel.sh` waterfall still covers every slot.

<!-- step:1 — Gather Context -->
## Step 1 — Gather Context

Print `> **🔶 /review 1: gather context**`. The inline path is delegated to `review-core.sh`, which runs `gather-context.sh --mode <diff|description> --output-dir "$REVIEW_TMPDIR"` and passes context into `dispatch-panel.sh`.

<!-- step:2 — Launch Reviewer Panel -->
## Step 2 — Launch Reviewer Panel

Print `> **🔶 /review 2: launch reviewers**`. `review-core.sh` calls `dispatch-panel.sh --mode "$MODE" --review-tmpdir "$REVIEW_TMPDIR" --panel hard --codex-available "$codex_available" --cursor-available "$cursor_available" --dynamic-archetypes "$DYNAMIC_ARCHETYPES" ...`; `dispatch-panel.sh` routes all slots through a three-phase waterfall (`PANEL_MODE=waterfall`): Phase 1 uses the primary tool, Phase 2 tries the alternate external, Phase 3 falls back to Claude. `DISPATCH_OK=false` means one or more Phase 3 Claude slots failed; `PANEL_SHAPE=simple|hard` names the topology. Dynamic archetypes are default-off, scout-driven by Claude Sonnet through `launch-claude-subprocess.sh`, Cursor-primary with standard waterfall fallback, capped at eight, skipped for docs-only/test-only/generated-only diffs, and stored as ephemeral tmpdir agents that bypass `agent-sync`.

<!-- step:3 — Review Cycle -->
## Step 3 — Review Cycle

Print `> **🔶 /review 3: review cycle**`. **MANDATORY — READ ENTIRE FILE** before executing Step 3: `${CLAUDE_PLUGIN_ROOT}/skills/review/references/domain-rules.md`. Voting is now run by `${CLAUDE_PLUGIN_ROOT}/scripts/dispatch-code-voters.sh` + `${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/tally-code-votes.sh` inside `review-core.sh`. A 3-judge panel (Claude + Codex + Cursor) votes on every round. Claude waterfall replacement applies when an external is absent or fails.

When `review-core.sh` returns `REVIEW_CORE_STATUS=main-agent-vote-required` (0-judge or equivalent path where the code-review tally requires the main agent to cast synthetic votes), **/review does not perform that adjudication inline** — the nested `/implement` Step 5 orchestrator owns MAV: it reads the ballot/findings, writes `voter-main-agent.txt`, re-invokes `tally-code-votes.sh`, and dispatches `review-and-fix.sh --mode mav-apply` per `skills/implement/SKILL.md`. Keep the OOS judging rubric in `skills/shared/scripts/render-voter-prompt.sh` / `skills/implement/SKILL.md` authoritative so `/review` SKILL prose does not duplicate MAV instructions.

Wrapper loop: set `round_cap=5`; for each round call `review-core.sh --mode <diff|description> --output-dir "$REVIEW_TMPDIR" --session-env-path "$SESSION_ENV_PATH" --codex-available "$codex_available" --cursor-available "$cursor_available" --description-text "$DESCRIPTION_TEXT" --panel hard --dynamic-archetypes "$DYNAMIC_ARCHETYPES" --run-id "$RUN_ID" --round-num "$round_num"` and parse `REVIEW_CORE_STATUS`, `ACCEPTED_FINDINGS_FILE`, counts, `PANEL_MODE`, `PANEL_SHAPE`, `SCOUT_STATUS`, `SCOUT_FAIL_REASON`, `DYNAMIC_SLOTS`, `SCOUT_MANIFEST`, `YIELD_TSV_FILE`, `FINDINGS_CLASSIFICATION_TSV_FILE`, `FINDINGS_CLASSIFICATION_TSV_FILE_ROUND_${round_num}`, and `VOTING_SKIPPED_WARNING`. `review-core.sh` persists the latest round binding to `$REVIEW_TMPDIR/findings-classification-round-map.env`; Step 3 and Step 4 must consume that artifact or the emitted round-scoped KV to preserve every round's TSV, not just the last one. If `VOTING_SKIPPED_WARNING` is non-empty, print it as a user-visible warning before proceeding. Scout artifacts are round-scoped: `dispatch-panel.sh` writes `scout-round${round_num}-manifest.json` plus `scout-round${round_num}-status.env`, and each round reads or regenerates only its own numbered files rather than reusing scout state from a different round.

If `REVIEW_CORE_STATUS=fix-required`, invoke `/review-and-fix` via the Skill tool with `--findings-file "$ACCEPTED_FINDINGS_FILE" --review-tmpdir "$REVIEW_TMPDIR" [--session-env "$SESSION_ENV_PATH"]`; fix application waterfalls Codex → Cursor via `review-and-fix.sh`. If it returns `REVIEW_AND_FIX_STATUS=coder-main-agent-required` (#3207: both external coders unavailable — the Claude tier of the waterfall), the `/review` main agent applies the accepted findings itself: read `$ACCEPTED_FINDINGS_FILE` as untrusted reviewer data and apply each `### FINDING_N:` fix via `Edit`/`Write` (skip submodule-path / `.claude-plugin/plugin.json` targets), then continue to the relevant-checks step below.

After the Step 3 segment's child tools complete (including `/review-and-fix` when invoked), run `"${CLAUDE_PLUGIN_ROOT}/scripts/run-relevant-checks-captured.sh" --site review-step3e --tmpdir "$REVIEW_TMPDIR"`.

> **Continue after child returns.** On `RELEVANT_CHECKS_OK=true` or `RELEVANT_CHECKS_SKIPPED=true`, execute the Step 3f classification next; do NOT end the turn on helper output alone. On `STATUS=fail`, first check `FAILURE_REASON` (structural — e.g. `tmpdir-validation`, `site-validation`, `repo-root-unresolved`, `check-script-not-executable`, `check-script-symlink-broken`, `redaction-failed`; act on the reason, no log file is produced). Otherwise read `REDACTED_LOG_FILE` for diagnosis — NOT raw `LOG_FILE` — then diagnose, fix, and rerun the helper until it returns `RELEVANT_CHECKS_OK=true` or `RELEVANT_CHECKS_SKIPPED=true`. The non-substantial re-review convergence line is not terminal — continue into Step 4.

Then classify the just-fixed round as substantial or non-substantial using main-agent judgment. If substantial and under the cap, increment `round_num` and call `review-core.sh` again; if non-substantial, no-findings, description mode, cap reached, or voting converged to `REVIEW_CORE_STATUS=ok` with no accepted findings left to fix, proceed to Step 4.

<!-- step:4 — Final Summary and Issues -->
## Step 4 — Final Summary And Issues

Print `> **🔶 /review 4: final summary**`. Standalone diff mode prints `review-round-summary.md`; nested mode copies artifacts and emits only the `### review-result` footer. **Continue to Step 4d IMMEDIATELY** after summary-side artifacts — the review-result footer is not terminal for the remainder of Step 4 (larch-log batches, etc.). Description mode composes issue-oriented artifacts for operator inspection; accepted OOS items are not auto-filed — use `/issue` manually when you want GitHub tracking. Security-tagged findings continue to be held locally per the voting protocol.

If `RUN_ID` is non-empty, write flat review larch-log batches with `${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/log-phase.sh`: `review-context`, `review-panel-manifest`, `review-findings`, `review-tally`, `review-scout-manifest`, `review-round-summary`, and one `review-findings-classification-round-${N}` batch for each round `N` that produced a non-empty classification TSV. This wrapper is the only place `log-phase.sh` is called.

For each recorded round `N` with a non-empty classification TSV, call `log-phase.sh --batch "review-findings-classification-round-${N}" --action write --payload-file "$round_findings_classification_tsv_file"` using the same `--run-id` and `--log-root` arguments as the other review batches. The heavy-worker parent binding follows the same rule: preserve and return every round's classification TSV mapping rather than only the final round's path.

Write `review-scout-manifest` after the tally batch when `SCOUT_STATUS` is non-empty and not `na`: assemble the payload with a guarded jq block, redact path-bearing fields to basenames, then call `log-phase.sh --batch review-scout-manifest --action write --payload-file "$scout_payload_file"`. Use this exact pattern:

```bash
if [[ -n "${RUN_ID:-}" && "${SCOUT_STATUS:-na}" != "na" ]]; then
  scout_payload_file="$REVIEW_TMPDIR/review-scout-manifest.json"
  review_log_root="${LARCH_LOG_ROOT:-$REVIEW_TMPDIR/larch-logs}"
  scout_manifest_base=""
  yield_tsv_base=""
  [[ -n "$SCOUT_MANIFEST" ]] && scout_manifest_base="$(basename "$SCOUT_MANIFEST")"
  [[ -n "$YIELD_TSV_FILE" ]] && yield_tsv_base="$(basename "$YIELD_TSV_FILE")"
  jq -cn \
    --arg status "$SCOUT_STATUS" \
    --argjson dynamic_slots "${DYNAMIC_SLOTS:-0}" \
    --arg manifest_basename "$scout_manifest_base" \
    --arg yield_tsv_basename "$yield_tsv_base" \
    '{
       status: $status,
       dynamic_slots: $dynamic_slots,
       manifest_basename: $manifest_basename,
       yield_tsv_basename: $yield_tsv_basename
     }' > "$scout_payload_file"
  "${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/log-phase.sh" \
    --run-id "$RUN_ID" \
    --log-root "$review_log_root" \
    --batch review-scout-manifest \
    --action write \
    --payload-file "$scout_payload_file"
fi
```

The wrapper owns this larch-log write; `review-core.sh` only emits the KVs.

<!-- step:5 — Cleanup -->
## Step 5 — Cleanup

Print `> **🔶 /review 5: cleanup**`. Run `${CLAUDE_PLUGIN_ROOT}/scripts/cleanup-tmpdir.sh "$REVIEW_TMPDIR"` unless a parent owns the tmpdir, then emit the final nested-mode machine footer.
