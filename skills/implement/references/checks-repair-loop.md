**Consumer**: `/implement` checks-failure orchestrator at the five SKILL sites: Step 3, Step 5 self-review, Step 5 MAV, Step 5 coder-main-agent-required, and Step 6.
**Contract**: normative `checks repair-loop` invocation, stdout KV parse-and-branch rules (`NEXT_ACTION`, optional tail and ledger keys), outer main-agent-edit re-entry, and default stall routing.
**When to load**: **MANDATORY — READ ENTIRE FILE** before handling `STATUS=fail` at any of those sites; do not invoke `checks repair-loop` or branch on repair outcomes without loading this file first.

## 1. Structural gate, all sites

On `STATUS=fail`, first check for `FAILURE_REASON`.

Structural reasons include `tmpdir-validation`, `site-validation`, `repo-root-unresolved`, `check-script-not-executable`, `check-script-symlink-broken`, and `redaction-failed`.

Act on the reason.
Do not invoke repair-loop when no `REDACTED_LOG_FILE` exists.
Then route to the default stall semantics in section 4: set `STALL_TRACKING=true`, skip to Step 18, and do not proceed on the site success path.

## 2. Repair-loop invocation

When `REDACTED_LOG_FILE` is present, run:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" checks repair-loop --tmpdir "$IMPLEMENT_TMPDIR" --site <lint-site> [--checks-site <capture-site>] --checks-log "$REDACTED_LOG_FILE"
```

Bind and reuse the pinned site pair for every invocation in section 4, including post-main-agent re-entries:

- Step 3: `--site step3`
- Step 5 self-review: `--site step5-self-review`
- Step 5 MAV and coder-main-agent-required: `--site step5-mav --checks-site step5-review-fixes`. The capture fence stays `run-step-checks.sh --site step5-review-fixes`. Repair-loop follows the lint-fix site, not the capture site. **Never** omit `--checks-site` on re-entry. Defaulting would run internal re-checks under `step5-mav` instead of `step5-review-fixes`.
- Step 6: `--site step6`

## 3. Parse stdout before branching on exit code

Use key-based extraction for these keys before checking the Bash exit code:

- `NEXT_ACTION`
- `STDERR_TAIL_PATH`
- `CODER_LOG_FILE`
- All `LINT_FIX_LEDGER_*` keys when present

Exit-code contract:

- Exit `0` with `NEXT_ACTION=continue` or `NEXT_ACTION=main-agent-edit` is success.
- Exit `1` with `NEXT_ACTION=stall` is the normal terminal stall path. Parse KVs from captured stdout and route to stall. Do not treat non-zero exit alone as an orchestrator hard failure before KV parse.
- Exit `2` for argument or validation failure still prints `NEXT_ACTION=stall`. Parse KVs first, then route to stall.

## 4. Branch semantics

### `NEXT_ACTION=continue`

Treat this as equivalent to `RELEVANT_CHECKS_OK=true` or `RELEVANT_CHECKS_SKIPPED=true` at the call site.
Do not re-invoke `run-step-checks.sh`.
Proceed on the site's success path.

### `NEXT_ACTION=main-agent-edit`

When `LINT_FIX_LEDGER_READY=true`, record one escalation before Main Claude Edit/Write. Pass the parsed `LINT_FIX_LEDGER_*` fields from section 3 verbatim; do not invent site/trigger tokens. See **Escalation recording owners** in `${CLAUDE_PLUGIN_ROOT}/skills/implement/SKILL.md` and `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/stall-recovery.md` for ownership and dedup rules.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" stall-recovery record-escalation --implement-tmpdir "$IMPLEMENT_TMPDIR" --site "$LINT_FIX_LEDGER_SITE" --trigger "$LINT_FIX_LEDGER_TRIGGER" --step "$LINT_FIX_LEDGER_STEP" --phase "$LINT_FIX_LEDGER_PHASE" --dispatcher "$LINT_FIX_LEDGER_DISPATCHER" --exit-code "$LINT_FIX_LEDGER_EXIT_CODE" --failure-detail-log "$LINT_FIX_LEDGER_FAILURE_DETAIL_LOG"
```

Stable lint-fix site/trigger tokens come from repair-loop stdout (for example `step3` / `main-agent-required`, `step5-self-review` / `main-agent-required`, `step5-mav` / `main-agent-required`, `step6` / `main-agent-required`). Use the parsed values, not the capture-site label.

Read tail paths when present.
Repair via main-agent Edit/Write.

Then re-run the site capture helper: `run-step-checks.sh` at the site's capture site.
On `STATUS=fail` with `REDACTED_LOG_FILE`, re-invoke `checks repair-loop` with the same pinned `--site` and optional `--checks-site` pair from section 2 for this call site and the updated `--checks-log`.
Do not pass only `--checks-log`.
Step 5 MAV and coder must repeat `--site step5-mav --checks-site step5-review-fixes`.
Repeat until `NEXT_ACTION` is `continue` or `stall`.
Preserve the structural `FAILURE_REASON` handling in section 1 on each re-entry.

### `NEXT_ACTION=stall`

Use the default implement contract: set `STALL_TRACKING=true` and skip to Step 18.
Stall recovery runs before the final report.
Step-local SKILL deltas may override this path.
Those overrides apply only at their sites.

Step 5 self-review has no override beyond the default stall routing.
Step 5 MAV and coder-main-agent-required terminal checks stalls are routing summaries at the repair-loop site. Do not invoke `step-5-resume.sh --final-round-num "$FINAL_ROUND_NUM" --record-only` or durable-seed inline here. Defer timing capture, forced `STALL_TRACKING=true`, and **Durable Bail to Step 18 Macro** execution to the main-agent handoff paragraph and `--record-only` fence in `${CLAUDE_PLUGIN_ROOT}/skills/implement/SKILL.md`. Do not re-invoke the Step 5 loop wrapper.

## 5. In-step contract

The failure path is in-step.
It is not a halt.
Do not end the turn, summarize, or write a handoff message.
