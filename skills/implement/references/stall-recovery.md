# /implement Step 18a stall recovery

**Consumer**: `/implement` Step 18a.

**Contract**: Step 18a reports only terminal failures and escalation-success events. It never files or prints at first detection. `skills/implement/scripts/stall-recovery-report.sh` owns classification, attempts, canonical escalation recording, normalized outcome reads, and report composition.

## Canonical artifacts

Use these `$IMPLEMENT_TMPDIR` paths for `/implement`:

- `stall-recovery-attempts.env`
- `stall-recovery-escalation-ledger.tsv`
- `stall-recovery-escalation-fallback.tsv`
- `stall-recovery-escalation-record-failure.env`
- `stall-recovery-terminal-report.env`
- `stall-recovery-escalation-success.env`
- `stall-recovery-classification.env`
- `stall-recovery-sensitive-corpus.env`
- `stall-recovery-issue-input.md`
- `stall-recovery-chat-print.md`
- `stall-recovery-operator-action-record.md`
- `stall-recovery-operator-action.env`
- `stall-recovery-root-cause.md`
- `stall-recovery-bounded-root-cause.md`
- `stall-recovery-title.txt`

The helper keeps internal seams for a later `/design` profile. Do not add public generic profile flags in this part.

## Step 18a procedure for active stalls

1. **Resolve stall tracking.** Read in-memory state, then `ship-pr-state.sh`, `finalize-state.sh`, and `session-env.sh`. If every layer is false or empty, skip active-stall recovery and allow Step 18a.5 to run outside this gate.
2. **Initialize attempts.** Run `stall-recovery-report.sh init-attempts --implement-tmpdir "$IMPLEMENT_TMPDIR" --attempts-file "$IMPLEMENT_TMPDIR/stall-recovery-attempts.env"`.
3. **Classify.** Pass any validated `BAIL_FAILURE_DETAIL_LOG`. The helper writes `stall-recovery-classification.env`, including `MATCHED_CLASSIFIER_PATTERN` and dispatcher identity when known.
4. **Do not file on first detection.** First detection only classifies, records attempts, and decides retry or terminal routing.
5. **Retry dispatch.** Respect the unchanged retry caps from `stall-recovery-report.md`. Record only branches that hand work to Main Claude. Do not record ordinary retries or reships. Re-invoke `${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/step-8-ship.sh` (same immediate-background fence: `run_in_background: true`, `timeout: 21600000`); wait for `<task-notification>` before advancing.
6. **Record prompt-side Main Claude handoffs before edits.** Call `record-escalation` before Step 18a inline `step2-impl` repair and before inline `step8-shippr` repair when Step 18a itself owns the repair. Stable owner tokens are `step2-impl` and `step8-shippr`.
7. **Success after recovery.** Clear stall state with `clear-stall`. Do not file here. Success-with-ledger reporting is owned only by Step 18a.5.
8. **Terminal failure.** Seed durable terminal stall state with `seed-terminal-state`. Main Claude must investigate before report composition and write `stall-recovery-root-cause.md`. If Tier B may be used, also write `stall-recovery-bounded-root-cause.md`, `stall-recovery-title.txt`, and `stall-recovery-sensitive-corpus.env`. Then call `compose-report --report-kind terminal-failure` exactly once. Tier A uses `--surface issue-input` and then `/larch:issue --input-file`; Tier B uses `--surface chat-print`. Write `stall-recovery-terminal-report.env` atomically after the issue is filed, after Tier B is printed, or after an operator-action skip result.
9. **Operator action.** If the root-cause verdict is `operator-action`, compose-report writes the non-filing record and sentinel. Do not file or print a public report.

## Step 18a.5 escalation-success procedure

Run this after the active stall gate and before Step 18b teardown.

Skip when any predicate is true:

- `stall-recovery-terminal-report.env` exists.
- `stall-recovery-escalation-success.env` exists.
- `stall-recovery-report.sh normalize-outcome` does not emit `IMPLEMENT_OUTCOME_SUCCEEDED=true`.
- Any observed `STALL_TRACKING` layer is true.
- No escalation evidence exists.

Escalation evidence is only:

- non-empty canonical ledger
- non-empty fallback ledger
- non-empty record-failure marker
- tagged `record-escalation` Tool Failure entries

Generic Tool Failures do not count. Missing attempts history is initialized as zero attempts.

If eligible, Main Claude reads validated failure detail, `ship-pr-state.sh`, `finalize-state.sh`, `session-env.sh`, attempts, classification, ledger, fallback evidence, record-failure marker, execution issues, run-log pointer when present, and prompt-state values it used. It writes root-cause artifacts for why the script loop needed Main Claude. Then it writes the prompt-state sensitive supplement immediately before `compose-report --report-kind escalation-success`.

Tier A files through `/larch:issue --input-file` after full-output secret redaction. Tier B prints `stall-recovery-chat-print.md` only. Write `stall-recovery-escalation-success.env` atomically after filed, printed, or operator-action skip result.

## Tier policy

Tier A applies only when `is-larch-dev-clone` is true and `FORKED_TARGET=false`. It bypasses TSV allowlists and redacts the full public issue input, including headings. It may include run linkage, branch, PR URL, validated logs, run-log pointer, full attempts, escalation ledger, root-cause finding, and verbatim bail reason after redaction.

Tier B covers consumer repos and forked runs. It prints through chat only. It uses allowlisted machine fields plus bounded root-cause prose. Bounded prose and title validation reject client repo names, branch names, paths, PR URLs, plan text, issue text, state-file client values, evidence-log values, attempts, ledger, fallback evidence, record-failure markers, run-log pointers, and prompt-state supplement tokens. Allowlisted larch operational terms are exempt.

## Root-cause finding schema

```text
verdict=larch-defect|environment|operator-action
confidence=low|medium|high
summary=<single-line>

<finding prose with durable evidence citations>
```

The finding must distinguish observation from inference and cite evidence by path or artifact name.

## Ship-pr and script handoff ownership

- `run-step5-review.sh` records `coder-main-agent-required` directly.
- Step 5 `main-agent-vote-required` is emitted as `STEP5_REVIEW_LEDGER_*` for the prompt side to record once.
- `lint-fix-loop.sh` emits `LINT_FIX_LEDGER_*` only for `main-agent-required` paths.
- Python `ship.py` emits ledger-ready JSON keys only for Step 8+ `NEEDS_USER_INPUT` handoffs.
- Bash `ship-pr.sh` emits ledger-ready data for opt-in handoffs and returns before recovery-waterfall edits on ship-pr-internal lint-fix `main-agent-required`.
- Clean retries, reships, and health-only paths do not record escalation events.

Report target stays unchanged in this part.
