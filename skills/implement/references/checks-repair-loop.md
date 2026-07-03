**Consumer**: `/implement` checks-failure orchestrator at folded Step 3, Step 5 self-review, Step 5 MAV, Step 5 coder-main-agent-required, and Step 6 sites.
**Contract**: normative `checks repair-loop` invocation, stdout KV parse-and-branch rules (`NEXT_ACTION`, optional tail and ledger keys), outer main-agent-edit re-entry, and default stall routing.
**When to load**: **MANDATORY — READ ENTIRE FILE** before handling `STATUS=fail` at any of those sites; do not invoke `checks repair-loop` or branch on repair outcomes without loading this file first.

## 1. Structural gate, all sites

On `STATUS=fail`, or folded-site composite `NEXT_ACTION=checks-failed`, first check for `FAILURE_REASON`.

Structural reasons include `tmpdir-validation`, `site-validation`, `repo-root-unresolved`, `check-script-not-executable`, `check-script-symlink-broken`, and `redaction-failed`.

Act on the reason.
Do not invoke repair-loop when no `REDACTED_LOG_FILE` exists.
For prompt-side diagnosis, prefer `DIGEST_FILE` when it is present and readable. Fall back to `REDACTED_LOG_FILE` when the digest is absent, unreadable, or insufficient.
At folded sites, key-scan the full composite stdout for both `DIGEST_FILE` and `REDACTED_LOG_FILE`, not only the first physical composite line. Bind `DIGEST_FILE` for diagnosis and reserve `REDACTED_LOG_FILE` for repair-loop input.
Before skipping to Step 18 on this no-log path, whitespace-token-scan the first physical line of captured composite stdout for `EXIT_CODE`, `FAILURE_REASON`, and `PHASE`. Mirror `FAILURE_REASON` into `IMPLEMENT_BAIL_REASON` and `FINAL_BAIL_REASON`. Set `STALL_STEP` from the pinned site (`3` for `--site step3`, `6` for `--site step6`, `5` for Step 5 self-review). Default `PHASE` to `checks` when the composite line omits it.
Then route to the default stall semantics in section 4: set `STALL_TRACKING=true`, skip to Step 18, and do not proceed on the site success path.

## 2. Repair-loop invocation

When `REDACTED_LOG_FILE` is present, run:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" checks repair-loop --tmpdir "$IMPLEMENT_TMPDIR" --site <lint-site> [--checks-site <capture-site>] --checks-log "$REDACTED_LOG_FILE"
```

Bind and reuse the pinned site pair for every invocation in section 4, including post-main-agent re-entries:

- Step 3: `--site step3`. The folded composite launcher is `python/cli.py implement checks-commit-route --checks-site step3 --commit-site step4 --rebase-checkpoint-4r --forked-target "${forked_target:-false}"`.
- Step 5 self-review: `--site step5-self-review`. The folded composite launcher is `python/cli.py implement checks-commit-route --checks-site step5-self-review --commit-site step5-self-review`.
- Step 5 MAV and coder-main-agent-required: `--site step5-mav --checks-site step5-review-fixes`. The folded composite launcher is `python/cli.py implement checks-step5-resume --checks-site step5-review-fixes --final-round-num "$FINAL_ROUND_NUM"`. Repair-loop follows the lint-fix site, not the capture site. **Never** omit `--checks-site` on re-entry. Defaulting would run internal re-checks under `step5-mav` instead of `step5-review-fixes`.
- Step 6: `--site step6`. The initial orchestrator folded composite launcher is `skills/implement/scripts/step-6-entry.sh --forked-target "${forked_target:-false}"` with the change gate active. All Step 6 post-repair re-entries, including `NEXT_ACTION=continue` and `NEXT_ACTION=main-agent-edit`, use `skills/implement/scripts/step-6-entry.sh --forked-target "${forked_target:-false}" --force-checks true` so the checks leg always re-runs even when repair leaves the tree matching pre-review baselines. Step 6 repair re-entry must not use the bare `checks-commit-route` launcher and must not omit `--force-checks true`.

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

Use this site split as the sole normative rule.

- Folded sites (Step 3, Step 5 self-review, Step 5 MAV/coder, Step 6): re-run the section 2-pinned composite launcher with identical argv before any success-path routing. For Step 6 only, identical argv means the post-repair re-entry launcher `skills/implement/scripts/step-6-entry.sh --forked-target "${forked_target:-false}" --force-checks true`, not the initial orchestrator argv without `--force-checks true`.

### `NEXT_ACTION=main-agent-edit`

When `LINT_FIX_LEDGER_READY=true`, record one escalation before Main Claude Edit/Write. Pass the parsed `LINT_FIX_LEDGER_*` fields from section 3 verbatim; do not invent site/trigger tokens. See **Escalation recording owners** in `${CLAUDE_PLUGIN_ROOT}/skills/implement/SKILL.md` and `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/stall-recovery.md` for ownership and dedup rules.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" stall-recovery record-escalation --implement-tmpdir "$IMPLEMENT_TMPDIR" --site "$LINT_FIX_LEDGER_SITE" --trigger "$LINT_FIX_LEDGER_TRIGGER" --step "$LINT_FIX_LEDGER_STEP" --phase "$LINT_FIX_LEDGER_PHASE" --dispatcher "$LINT_FIX_LEDGER_DISPATCHER" --exit-code "$LINT_FIX_LEDGER_EXIT_CODE" --failure-detail-log "$LINT_FIX_LEDGER_FAILURE_DETAIL_LOG"
```

Stable lint-fix site/trigger tokens come from repair-loop stdout (for example `step3` / `main-agent-required`, `step5-self-review` / `main-agent-required`, `step5-mav` / `main-agent-required`, `step6` / `main-agent-required`). Use the parsed values, not the capture-site label.

Read tail paths when present.
Repair via main-agent Edit/Write.

Then refresh any orchestrator-owned artifacts changed by the repair. Step 3 main-agent fallback rebinds repo root and reruns `recovery-paths` in one fence, then rewrites the implementation commit message before re-entry:

```bash
REPO_ROOT="$(git rev-parse --show-toplevel)"
if [ -n "$REPO_ROOT" ]; then
  "$HOME/.cache/larch/sessions/implement-run-$PPID.sh" python/cli.py implement recovery-paths --repo-root "$REPO_ROOT" --tmpdir "$IMPLEMENT_TMPDIR" --capture-postlaunch --prelaunch-porcelain "$IMPLEMENT_TMPDIR/step2-prelaunch-porcelain.nul" --postlaunch-porcelain "$IMPLEMENT_TMPDIR/step2-postlaunch-porcelain.nul" --prelaunch-digests "$IMPLEMENT_TMPDIR/step2-prelaunch-content-digests.txt" --out-file "$IMPLEMENT_TMPDIR/implementation-commit-paths.nul"
fi
```

After the pathspec refresh fence succeeds, rewrite `$IMPLEMENT_TMPDIR/implementation-commit-message.txt` with the redacted Step 4 commit message synthesized from the current plan/issue context (same contract as Step 2.4 in `${CLAUDE_PLUGIN_ROOT}/skills/implement/SKILL.md`).

If `REPO_ROOT` is empty, follow the Step 2.4 `repo-root-unresolved` bail contract in `${CLAUDE_PLUGIN_ROOT}/skills/implement/SKILL.md` instead of calling `recovery-paths`. Then re-run the section 2-pinned composite launcher with identical argv. For Step 6 after main-agent repair edits, re-run `skills/implement/scripts/step-6-entry.sh --forked-target "${forked_target:-false}" --force-checks true` before any success-path routing or subsequent `checks repair-loop` invocation; do not reuse the initial orchestrator argv without `--force-checks true`.
On `STATUS=fail` or composite `NEXT_ACTION=checks-failed` with `REDACTED_LOG_FILE`, re-invoke `checks repair-loop` with the same pinned `--site` and optional `--checks-site` pair from section 2 for this call site and the updated `--checks-log`.
If a new `DIGEST_FILE` is present on re-entry, replace the previous digest for prompt-side diagnosis. Keep the updated `REDACTED_LOG_FILE` as the repair-loop input.
Do not pass only `--checks-log`.
Step 5 MAV and coder must repeat `--site step5-mav --checks-site step5-review-fixes`.
Repeat until repair-loop `NEXT_ACTION` is `continue` or `stall`; `continue` still means re-run the same composite launcher before success routing. On Step 6, both `continue` and `main-agent-edit` repair paths must use `skills/implement/scripts/step-6-entry.sh --forked-target "${forked_target:-false}" --force-checks true`; never re-enter Step 6 repair via bare `checks-commit-route`.
Preserve the structural `FAILURE_REASON` handling in section 1 on each re-entry.

### `NEXT_ACTION=stall`

Before skipping to Step 18, bind `EXIT_CODE`, `FAILURE_REASON` (into `IMPLEMENT_BAIL_REASON` and `FINAL_BAIL_REASON`), `STALL_STEP`, and `PHASE` from captured composite stdout when those prompt-side values are not already set. Whitespace-token-scan the first physical line the same way as section 1.

Use the default implement contract: set `STALL_TRACKING=true` and skip to Step 18.
Applies to Step 3, Step 6, and Step 5 self-review only.
Stall recovery runs before the final report.
Step-local SKILL deltas may override this path.
Those overrides apply only at their sites.

Step 5 self-review has no override beyond the default stall routing.
Step 5 MAV and coder-main-agent-required terminal checks stalls are routing summaries at the repair-loop site. Do **not** skip to Step 18 at this site. Continue to the main-agent handoff paragraph in `${CLAUDE_PLUGIN_ROOT}/skills/implement/SKILL.md`; that paragraph performs `--record-only` timing capture, then applies the **Durable Bail** body in `${CLAUDE_PLUGIN_ROOT}/skills/implement/references/step5-review-branches.md` before skipping to Step 18. Do not invoke `step-5-resume.sh --final-round-num "$FINAL_ROUND_NUM" --record-only` or durable-seed inline here. Do not re-invoke the Step 5 loop wrapper.

## 5. In-step contract

The failure path is in-step.
It is not a halt.
Do not end the turn, summarize, or write a handoff message.
