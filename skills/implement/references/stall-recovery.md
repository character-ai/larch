# /implement Step 18a stall recovery

**Consumer**: `/implement` Step 18a.

**Contract**: Step 18a reports terminal failures only. It never files or prints at first detection. `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" stall-recovery` owns classification, attempts, canonical escalation recording, normalized outcome reads, and report composition.

**When to load**: MANDATORY before executing Step 18a active-stall recovery when `STALL_RECOVERY_REQUIRED=true`. Load before changing active-stall recovery report composition, escalation recording, or normalized outcome handling.

## Canonical artifacts

Use these `$IMPLEMENT_TMPDIR` paths for `/implement`:

- `stall-recovery-attempts.env`
- `stall-recovery-escalation-ledger.tsv`
- `stall-recovery-escalation-fallback.tsv`
- `stall-recovery-escalation-record-failure.env`
- `stall-recovery-terminal-report.env`
- `stall-recovery-classification.env`
- `stall-recovery-sensitive-corpus.env`
- `stall-recovery-issue-input.md`
- `stall-recovery-chat-print.md`
- `stall-recovery-operator-action-record.md`
- `stall-recovery-operator-action.env`
- `stall-recovery-root-cause.md`
- `stall-recovery-bounded-root-cause.md`
- `stall-recovery-title.txt`
- `stall-recovery-tier-a-attempts.md`
- `stall-recovery-tier-a-escalation.md`
- `stall-recovery-tier-a-root-cause.md`
- `stall-recovery-bounded-attempts.md`
- `stall-recovery-bounded-escalation-summary.md`
- `stall-recovery-bounded-root-cause-public.md`

The helper keeps internal seams for a later `/design` profile. Do not add public generic profile flags in this part.

## Step 18a procedure for active stalls

1. **Resolve stall tracking.** Read in-memory state, then `ship-pr-state.sh`, `finalize-state.sh`, and `session-env.sh`. If every layer is false or empty, skip active-stall recovery.
2. **Initialize attempts.** Run `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" stall-recovery init-attempts --implement-tmpdir "$IMPLEMENT_TMPDIR" --attempts-file "$IMPLEMENT_TMPDIR/stall-recovery-attempts.env"`.
3. **Classify.** Run:

```bash
python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" stall-recovery classify \
  --implement-tmpdir "$IMPLEMENT_TMPDIR" \
  --attempts-file "$IMPLEMENT_TMPDIR/stall-recovery-attempts.env" \
  --in-memory-stall-tracking "${STALL_TRACKING:-false}" \
  --stall-step "${STALL_STEP}" \
  --phase "${PHASE:-checks}" \
  --bail-reason "${IMPLEMENT_BAIL_REASON:-${FINAL_BAIL_REASON:-}}" \
  --exit-code "${EXIT_CODE:-unknown}" \
  [--failure-detail-log "$BAIL_FAILURE_DETAIL_LOG"]
```

Bind `EXIT_CODE` from captured composite stdout before Step 18 when durable stall seeding omits it (for example `checks-commit-route` `checks-child-failed` with no `REDACTED_LOG_FILE`). Pass any validated `BAIL_FAILURE_DETAIL_LOG`. The helper writes `stall-recovery-classification.env`, including `MATCHED_CLASSIFIER_PATTERN` and dispatcher identity when known.
4. **Do not file on first detection.** First detection only classifies, records attempts, and decides retry or terminal routing. The protected-path and submodule-restricted operator warnings are allowed first-detection text only for their matching dispatcher bail reasons:
   - `protected-path-edit-required-out-of-scope` warns on `.claude-plugin/plugin.json` and classifies as `FAILURE_CLASS=protected-path`.
   - `submodule-edit-required-out-of-scope` classifies as `FAILURE_CLASS=submodule-restricted` with `RESUME_HINT=none`, then prints `**⚠ /implement: implementer bailed on submodule-restricted path; submodule edits are blocked for Main Claude too. No automatic inline recovery will run.**`
5. **Retry dispatch.** Respect the retry caps from `python/stall-recovery-report.md`. Record only branches that hand work to Main Claude. Do not record ordinary retries or reships. Dispatch by `RESUME_HINT`. Retry semantics are class-specific. For protected-path stalls with `RESUME_HINT=step2-impl`, `step2-impl` means record escalation before edits, then Main Claude reads `$IMPLEMENT_TMPDIR/plan.txt` and implements inline; for protected-path stalls, Codex cannot edit the protected path. Continue through the normal current-run checks, commit, review, and ship sequence. For `submodule-restricted`, `RESUME_HINT=none`; it does not dispatch `step2-impl`, and no inline Step 2 repair runs for `submodule-restricted`. `step8-shippr` is the only retry branch that re-invokes `${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/step-8-ship.sh`; before the `run_in_background: true` launcher, run the foreground stale-handoff clear from SKILL.md Step 8+ in the same turn, then use the same immediate-background fence (`run_in_background: true`, `timeout: 21600000`) and wait for `<task-notification>` before advancing. `step5-review` resumes Step 5 review and reaches Step 8 only through the normal current-run sequence. `RESUME_HINT=checks-commit-route-retry` (`FAILURE_CLASS=transient-infra`, `MATCHED_CLASSIFIER_PATTERN=checks-leg-abandoned` or `MATCHED_CLASSIFIER_PATTERN=checks-child-sigterm`) means a `checks-commit-route` process died before writing any `STALL_TRACKING` evidence, left only a dead-PID `.bg-wait-active` marker, or the checks child exited by signal or an unresolvable exit code. For Step 3 (`implement-step3-checks`), re-invoke the same Step 3 composite launcher (identical argv) through the same immediate-background fence and wait for `<task-notification>`. Step 6 classifies `checks-child-sigterm` accurately but does not get automatic retry dispatch. For `--self-review` Step 5 (`implement-step5-self-review`), re-invoke `python/cli.py implement checks-commit-route --checks-site step5-self-review --commit-site step5-self-review` through the same immediate-background fence and wait for `<task-notification>`. Genuine checks-content failures with a positive composite `EXIT_CODE` forwarded through `--exit-code` still classify as `contract-failure` / `RESUME_HINT=none`. Signal-killed or unresolvable `EXIT_CODE` values on `checks-child-failed` classify as `transient-infra` per the `checks-child-sigterm` pattern above.
6. **Record prompt-side Main Claude handoffs before edits.** Call `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" stall-recovery record-escalation` before Step 18a inline `step2-impl` repair, and before inline `step8-shippr` repair **only when Step 18a itself performs Main Claude code edits** (for example Main Claude implementing inline after a `protected-path` bail, or fixing CI after the Python ship driver emitted `ledger_ready=true`). A reship with no Main Claude code edits is an ordinary reship and must not record an escalation event: a `FAILURE_CLASS=transient-infra` / `RESUME_HINT=step8-shippr` reship runs the foreground stale-handoff clear, then re-invokes `step-8-ship.sh` directly with no `record-escalation` call. Stable owner tokens are `step2-impl` and `step8-shippr`; pass one of those `_COMMON_TRIGGERS` owner tokens as `--trigger`, never the stall detail or classifier output (for example `no-ci-checks-observed` is not a valid trigger).
7. **Success after recovery.** Run `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" stall-recovery clear-stall --implement-tmpdir "$IMPLEMENT_TMPDIR"`. Proceed as recovery success only when it emits `CLEARED=true`. Treat prompt-side in-memory stall tracking as cleared for the next normalization call.
8. **Terminal failure.** Seed durable terminal stall state with `seed-terminal-state`. Main Claude must investigate before report composition and write `stall-recovery-root-cause.md`. If Tier B may be used, also write `stall-recovery-bounded-root-cause.md`, `stall-recovery-title.txt`, and `stall-recovery-sensitive-corpus.env`. Then call `compose-report --report-kind terminal-failure` exactly once. Tier A uses `--surface issue-input` as artifact composition only, then runs `dedup-tier-a-report` before `/larch:issue`. Tier B uses `--surface chat-print`; the helper resolves upstream larch, dedups, and files or comments unless dry-run is active. Write `stall-recovery-terminal-report.env` atomically after filed, commented, fallback-printed, dry-run, or operator-action skip result.
9. **Operator action.** If the root-cause verdict is `operator-action`, compose-report writes the non-filing record and sentinel. Do not file or print a public report.

## Tier policy

Tier A applies only when `is-larch-dev-clone` is true and `FORKED_TARGET=false`. It bypasses TSV allowlists and redacts the full public issue input, including headings. It may include run linkage, branch, PR URL, validated logs, run-log pointer, full attempts, escalation ledger, root-cause finding, and verbatim bail reason after redaction.

Tier B covers consumer repos and forked runs. It files or comments in the resolved upstream larch repository on success, and prints through chat only on fallback or dry-run. It uses allowlisted machine fields plus bounded root-cause prose. Bounded prose and title validation reject client repo names, branch names, paths, PR URLs, plan text, issue text, state-file client values, evidence-log values, attempts, ledger, fallback evidence, record-failure markers, run-log pointers, and prompt-state supplement tokens. Allowlisted larch operational terms are exempt.

## Root-cause finding schema

```text
verdict=larch-defect|environment|operator-action
confidence=low|medium|high
summary=<single-line>

<finding prose with durable evidence citations>
```

The finding must distinguish observation from inference and cite evidence by path or artifact name.

## Ship-pr and script handoff ownership

- `review-and-fix step5` records `coder-main-agent-required` directly.
- Step 5 `main-agent-vote-required` is emitted as `STEP5_REVIEW_LEDGER_*` for the prompt side to record once.
- `python/cli.py checks lint-fix` emits `LINT_FIX_LEDGER_*` only for `main-agent-required` paths.
- Python `ship.py` emits ledger-ready JSON keys only for Step 8+ `NEEDS_USER_INPUT` handoffs.
- The Python ship driver emits ledger-ready data for handoffs and returns before recovery-waterfall edits on ship-pr-internal lint-fix `main-agent-required`.
- Clean retries, reships, and health-only paths do not record escalation events.

## Filing flow

Tier A keeps the current `/larch:issue` filing target. It must:

1. Compose `issue-input` and treat compose output as artifact metadata only.
2. If dry-run is active, skip dedup and `/larch:issue`, then write the terminal sentinel with `STALL_RECOVERY_REPORT_STATUS=dry-run`.
3. Run `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" stall-recovery dedup-tier-a-report`.
4. Branch only on `STALL_RECOVERY_REPORT_STATUS`.
5. On `dedup-comment`, skip `/larch:issue`.
6. On `no-match` or `lookup-failed-open`, call `/larch:issue --input-file ... --no-dedup`.
7. On `fallback-print-required`, print the sanitized artifact instead of creating a duplicate.
8. After successful `/larch:issue`, run `normalize-issue-env` or an equivalent writer, persist `ISSUE_URL` and `ISSUE_NUMBER`, and emit `STALL_RECOVERY_REPORT_STATUS=filed`, `STALL_RECOVERY_REPORT_URL`, `STALL_RECOVERY_REPORT_ISSUE_URL`, and `STALL_RECOVERY_REPORT_ISSUE_NUMBER`.

Tier B now files public reports in the resolved upstream larch repository. It must:

1. Call `compose-report --surface chat-print`.
2. On `filed` or `dedup-comment`, print only a short notice using `STALL_RECOVERY_REPORT_URL`.
3. On `fallback-print-required`, print `stall-recovery-chat-print.md` for manual filing.
4. On `dry-run`, keep local artifact-only behavior.
5. On `skipped_operator_action`, keep the local sentinel and do not file.

`is-larch-dev-clone` selects the content tier only. It no longer decides whether a public report is filed. Tier B passes only bounded public comment payload files to the cross-repo helper: bounded attempts, allowlisted escalation site/trigger summaries, and bounded root-cause prose. It must not pass raw root-cause files, raw ledgers, full report bodies, raw logs, paths, branches, or run IDs to the Tier B comment path.

Public report dedup uses the `REPORT_DEDUP_SIGNATURE` marker, not retry `FAILURE_SIGNATURE`. The marker is exact `<!-- larch-stall:signature=<64-hex> -->`. Terminal signatures include only `report_kind`, `failure_class`, `step`, `phase`, and `safe_bail_token`. Escalation-success signatures add sanitized `escalation_site` and `escalation_trigger`. Dispatcher, matched classifier, evidence digests, paths, branches, run IDs, raw state, raw logs, and `skill=implement` stay out of the Part 2 seed.
