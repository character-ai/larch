## Goal
Implement issue #3992: [IMPLEMENTING] auto-error-reporting: port terminal-failure reporting to /design.

## Implementation Plan
## Plan

Port /design auto error reporting over the existing shared reporting and filing core.

- Add **generic profile flags** to `stall-recovery-report.sh`.
- Add an explicit **shared validation API** so /design staging does not fork safe-value logic.
- Keep existing `/implement` defaults byte-compatible.
- Use artifact prefix `design-failure` for /design.
- Stage /design terminal and escalation state in `$DESIGN_TMPDIR`.
- Add a mechanical terminal-state staging helper for prompt-owned hard halts.
- Move **Step 2b.5 decompose-panel retry exhaustion** reporting to the Split-path owner.
- Run the report gate from normal teardown and true hard-fail abort paths.
- File **at most one report per run**.
- Let **terminal failures win** over escalation-success reports on failed outcomes.
- Skip filing for `operator-action`, but always record the skip in chat-visible output and the run log.
- Keep Tier B bounded and log-tail-free.
- Keep KV-only script stdout channels free of final-summary prose.

## Failure, escalation, and teardown surface

**Terminal failure report:**

- `PLAN_WRITE_OK=false`, surfaced as `failed-plan-write`.
- `PUBLISH_OK=false` after `PLAN_WRITE_OK=true`, surfaced as `failed-publish`.
- `STEP3_REVIEW_LOOP_STATUS=postplan-failed`, surfaced as `failed-postplan`.
- Clarify-loop exhaustion or unrecovered clarify helper failure, surfaced as `failed-clarify` only when Step 0b reaches a hard halt.
- Step 2b.5 Split-path decompose-panel retry exhaustion after the second `PANEL_STATUS=panel-failed`, surfaced as `failed-judge-panel`.
- `design-publish.sh` exit `2` or unexpected hard helper failure, staged before abort.
- Publish-tail hard exits in Step 5c, surfaced as `failed-publish-tail`.

**Non-terminal panel degradation:**

- Current Step 3 statuses `panel-failed`, `tally-error`, and `degraded-empty-collector` remain **non-terminal** when they represent Gate B bypass degradation.
- They keep the current behavior: bypass Gate B through the fail-closed helper and continue to Step 3b, Step 4, and Gate C.
- They record degradation or escalation evidence for a later escalation-success report when the final outcome is successful.
- They must not write `design-failure-terminal-state.env`.
- They must not invoke a failed-panel final summary.
- They must not file a terminal bug on a later `approved` run.

**Step 2b.5 decompose-panel terminal collapse:**

- Decompose-panel retry exhaustion is owned by Step 2b.5 Split-path orchestration, not `design-step3-review.sh`.
- On the second `PANEL_STATUS=panel-failed`, Split-path stages `FAILURE_OUTCOME=failed-judge-panel`.
- It uses decompose-panel vocab tokens, including `SITE=decompose-panel` and `TRIGGER=decompose-panel-retry-exhausted`.
- It exports `SUMMARY_OUTCOME=failed-judge-panel`.
- It runs the existing Final summary block before exiting `/design` 1 when safe.
- It preserves `$DESIGN_TMPDIR`.
- `design-step3-review.sh` must not handle this terminal path.

**Operator action, no filing:**

- All `cancelled-*` final-summary outcomes.
- Validator operator **Cancel**.
- Clarify operator cancel.
- Any root-cause verdict `operator-action`.
- Operator-action paths write `design-failure-operator-action.env` before teardown can see an approved outcome with prior escalation evidence.
- Operator-action skips write:
  - a redacted run-log record or pointer.
  - `$DESIGN_TMPDIR/design-failure-operator-action-chat.md`.
- `render-final-summary.sh` prints `design-failure-operator-action-chat.md` after the summary body whenever it exists.
- This chat sidecar is the guaranteed operator-visible audit path.

**Escalation-success report on otherwise-successful runs:**

- Success allowlist is explicit:
  - `approved`.
  - `approved-partition`.
- `STEP3_REVIEW_LOOP_STATUS=main-agent-vote-required`.
- `STEP3_REVIEW_LOOP_STATUS=main-agent-apply-required`.
- `STEP3_REVIEW_LOOP_STATUS=postplan-operator-required`.
- Step 3 degradation statuses when they skip script-owned review and the run later succeeds:
  - `panel-failed`.
  - `tally-error`.
  - `degraded-empty-collector`.
- Validator autofix statuses `exhausted`, `failed`, `unavailable`, and `skipped-cycle-cap` at:
  - Step 2b.
  - Gate B / Step 3.5.
  - discussion-round2.
  - Step 5c.

## Terminal-state KV contract

`design-failure-terminal-state.env` is a strict, redacted KV file under `$DESIGN_TMPDIR`.

Required keys:

- `DESIGN_FAILURE_VERSION=1`
- `DESIGN_FAILURE_KIND=terminal`
- `FAILURE_OUTCOME=<failed-* token>`
- `STALL_STEP=<generic design step token>`
- `PHASE=<generic design phase token>`
- `SITE=<generic design site token>`
- `TRIGGER=<generic design trigger token>`
- `BAIL_REASON=<generic design bail token>`
- `EXIT_CODE=<integer or unknown>`
- `FAILURE_DETAIL_LOG=<path under $DESIGN_TMPDIR or empty>`
- `SOURCE_SCRIPT=<script or prompt-step token>`

Optional keys:

- `ROOT_CAUSE_HINT=larch-defect|environment|operator-action`
- `SUMMARY_OUTCOME=<failed-* token>`
- `OCCURRED_AT=<ISO-8601 timestamp>`
- `EVIDENCE_REF=<redacted local artifact name>`

Rules:

- The file contains **no raw user prompt, issue body, feature text, plan text, repo path, URL, or log tail**.
- `FAILURE_DETAIL_LOG` is accepted only when it is inside `$DESIGN_TMPDIR` and not a symlink.
- `design-stage-terminal-state.sh` is the shared writer for prompt-owned hard halts and script paths that lack a local writer.
- `design-failure-report.sh` revalidates this file before terminal classification.
- Generic helper calls from `design-failure-report.sh` pass explicit state overrides:
  - `--primary-state-file "$DESIGN_TMPDIR/design-failure-terminal-state.env"`
  - `--session-env-file "$DESIGN_TMPDIR/source-env.sh"`
  - `--finalize-state-file "$DESIGN_TMPDIR/finalize-state.sh"` when present.
- The generic helper must support terminal classification without `ship-pr-state.sh`.

## Shared validation API

`stall-recovery-report.sh` exposes generic-profile validation subcommands so /design callers reuse the safe-value layer.

**New validation subcommands:**

- `validate-token`
  - Inputs:
    - `--profile generic`
    - `--token-kind outcome|step|phase|site|trigger|bail|source-script|root-cause`
    - `--value <token>`
    - `--artifact-prefix design-failure`
    - `--implement-tmpdir "$DESIGN_TMPDIR"`
  - Output:
    - quiet KVs only, for example `VALID=true`.
  - Behavior:
    - exit `0` for accepted tokens.
    - exit non-zero for unknown, raw, path-like, URL-like, or sensitive values.
- `validate-terminal-state`
  - Inputs:
    - `--profile generic`
    - `--primary-state-file <candidate.env>`
    - `--artifact-prefix design-failure`
    - `--implement-tmpdir "$DESIGN_TMPDIR"`
  - Output:
    - quiet KVs only.
  - Behavior:
    - validate required keys, optional keys, design vocab, path confinement, symlink rejection, and redaction rules.
    - exit non-zero on any invalid value.

**Rules:**

- `design-stage-terminal-state.sh` calls `validate-token` before writing terminal state.
- `design-failure-report.sh` calls `validate-terminal-state` before terminal `classify`.
- No /design script sources private helper internals.
- No /design script duplicates the generic safe-value vocabulary.
- All validation calls pin `--implement-tmpdir "$DESIGN_TMPDIR"`.

## Teardown gate precedence

`design-failure-report.sh` owns the Step 18a.5-equivalent decision.

Decision order:

1. Validate `$DESIGN_TMPDIR`.
2. If `design-failure-terminal-report.env` exists, skip.
3. If `design-failure-escalation-success.env` exists, skip.
4. If `design-failure-operator-action.env` exists, write or repair operator-action chat and run-log audits, then skip filing.
5. If the outcome is `cancelled-*`, write operator-action audit artifacts and skip filing.
6. If the outcome is `failed-*` and terminal state exists, validate terminal state and compose a terminal report.
7. If the outcome is `failed-*` and terminal state is missing or invalid, fail closed to fallback print.
8. If the outcome is not in the success allowlist, skip escalation-success reporting.
9. If the outcome is successful and escalation evidence exists, compose an escalation-success report without terminal classification.
10. Otherwise skip.

Rules:

- Terminal reporting requires a failed outcome or a true hard-fail invocation.
- Escalation-success never fires on cancelled, failed, unknown, or missing outcomes.
- Escalation-success never fires when a terminal or operator-action sentinel exists.
- Terminal failure wins when a failed outcome has both terminal state and escalation evidence.
- Stale terminal state is ignored on successful outcomes.
- Panel degradation evidence alone never creates a terminal report.
- Step 2b.5 decompose-panel retry exhaustion is the terminal judge-panel surface.
- KV-only script stdout channels must not print final-summary prose.

## Files to modify/create

### UPDATED: skills/implement/scripts/stall-recovery-report.sh

Add generic parameterization without changing `/implement` behavior.

- Add a small global config layer:
  - `REPORT_PROFILE=implement|generic`.
  - `ARTIFACT_PREFIX=stall-recovery` by default.
  - `REPORT_SKILL_LABEL=/implement` by default.
  - `--primary-state-file`.
  - `--finalize-state-file`.
  - `--session-env-file`.
  - inline vocab overrides for step, phase, site, trigger, bail, dispatcher, and source-script tokens.
- Add public validation subcommands:
  - `validate-token`.
  - `validate-terminal-state`.
- Derive artifact filenames from `ARTIFACT_PREFIX`.
  - Default names remain exactly current `stall-recovery-*`.
  - /design uses `design-failure-*`.
- Add a generic-profile-only design vocab table in code.
  - Design steps: validator, postplan, publish, clarify, panel, judge-panel, step2b, step3, step5c.
  - Design phases: plan-write, publish, postplan, clarify-loop, judge-panel, validation, teardown.
  - Design sites: step2b, gate-b, step3-review, discussion-round2, step5c, design-publish, clarify-loop, judge-panel, decompose-panel.
  - Design triggers: main-agent-vote-required, main-agent-apply-required, postplan-operator-required, exhausted, failed, unavailable, skipped-cycle-cap, postplan-failed, panel-failed, tally-error, degraded-empty-collector, judge-panel-collapse, decompose-panel-retry-exhausted.
- Make `classify` honor generic state overrides.
  - Do not require `ship-pr-state.sh` when `--profile generic` supplies `--primary-state-file`.
  - Treat `design-failure-terminal-state.env` as the source of terminal classification.
  - Map the terminal-state KV contract into the existing classification model.
  - Reserve terminal classification for terminal-failure reporting only.
- Make `compose-report` honor generic state overrides.
  - Use `$DESIGN_TMPDIR/source-env.sh` through `--session-env-file`.
  - Include `source-env.sh` in sensitive-corpus discovery.
  - Support `--report-kind escalation-success` from ledger evidence without a terminal classify file.
- Make validation helpers call vocab-aware safe functions.
  - Preserve current hardcoded vocab as the default.
  - Accept design tokens only when `--profile generic` supplies the design vocab.
- Do not add design token rows to `stall-recovery-report-allowlists.tsv` unless a new Tier B field is exposed.
- Parameterize report strings:
  - `/implement` stays default.
  - /design reports render `/design`.
  - Titles use `[Bug] /design terminal:` and `[Bug] /design escalation:`.
- Add skill-aware public dedup seed when `--profile generic` is used.
  - Keep existing `/implement` seed unchanged.
  - Use a new generic seed version for design so signatures do not collide across skills.
- Accept `--implement-tmpdir "$DESIGN_TMPDIR"` on all generic helper calls from /design.
  - Use it for path confinement, symlink rejection, and sensitive corpus discovery.
- Keep existing public subcommand names.
- Accept generic flags before the subcommand and on subcommands that need them.
- Keep legacy test-only surfaces behind the current test env flag.

### UPDATED: skills/implement/scripts/stall-recovery-report.md

Document the generic profile.

- Replace the current “deferred to #3992” note with the implemented contract.
- List supported generic flags.
- Document state override flags for classify and compose.
- Document validation subcommands:
  - `validate-token`.
  - `validate-terminal-state`.
- Document artifact-prefix behavior.
- Document skill-aware dedup only for generic profile.
- Add /design token examples without making `/design` a first-class hardcoded arm.
- Document the `design-failure-terminal-state.env` mapping expected by generic callers.
- State that `/implement` defaults are unchanged.
- Clarify that escalation-success uses ledger evidence and `compose-report --report-kind escalation-success`, not terminal `classify`.
- Clarify that token vocab lives in safe-value helpers, not the Tier B field allowlist TSV.

### UPDATED: skills/implement/scripts/test-stall-recovery-report.sh

Add focused generic-profile coverage.

- Artifact-prefix writes `design-failure-*`.
- Default `/implement` filenames remain unchanged.
- Generic vocab accepts design tokens and rejects unknown tokens.
- `validate-token` accepts valid design tokens and rejects unknown tokens.
- `validate-terminal-state` accepts valid terminal state and rejects malformed state.
- Generic title/body say `/design`.
- `/implement` report signatures remain byte-stable.
- Generic signatures include skill/profile separation.
- Generic classify succeeds from `design-failure-terminal-state.env` without `ship-pr-state.sh`.
- Generic compose supports `--report-kind escalation-success` from ledger evidence without terminal classification.
- Generic classify and compose honor `--primary-state-file`, `--session-env-file`, and `--finalize-state-file`.
- All generic /design calls pin `--implement-tmpdir "$DESIGN_TMPDIR"`.
- Generic path validation rejects outside-tmpdir and symlinked `--failure-detail-log`.
- Tier B validation still rejects raw paths, URLs, and sensitive state.
- Cross-repo design-prefix dedup uses the design sensitive corpus.
- Sensitive corpus includes `$DESIGN_TMPDIR/source-env.sh`.

### UPDATED: scripts/file-failure-report-cross-repo.sh

Make Tier B cross-repo filing prefix-aware.

- Add `--sensitive-corpus-file`, defaulting to `stall-recovery-sensitive-corpus.env`.
- Add optional `--artifact-prefix` or equivalent prefix discovery only where needed.
- Pass the supplied sensitive corpus into `validate-tier-b-public-file`.
- Keep `/implement` defaults unchanged.
- Extend raw-body rejection to recognize both `/implement` and `/design` full-report headings.
- Preserve existing signature dedup behavior.
- Ensure duplicate /design Tier B reports post occurrence comments instead of falling back due to missing implement-named corpus files.

### UPDATED: scripts/file-failure-report-cross-repo.md

Document the prefix-aware filing contract.

- Document `--sensitive-corpus-file`.
- Document the default `/implement` corpus path.
- Document design-prefix Tier B behavior.
- Document duplicate occurrence comments for /design.
- Document fail-closed behavior for missing or invalid sensitive corpus files.

### UPDATED: scripts/test-file-failure-report-cross-repo.sh

Add design-prefix coverage.

- Default `/implement` corpus path remains unchanged.
- Explicit `--sensitive-corpus-file design-failure-sensitive-corpus.env` is honored.
- Duplicate /design Tier B filings dedup and comment.
- Raw full-report body rejection catches `/design` headings.
- Missing or invalid sensitive corpus fails closed to fallback behavior.

### NEW: skills/design/scripts/design-stage-terminal-state.sh

Create the shared terminal-state writer for prompt-owned and hard-fail paths.

Inputs:

- `--design-tmpdir`.
- `--outcome`.
- `--step`.
- `--phase`.
- `--site`.
- `--trigger`.
- `--bail-reason`.
- `--exit-code`.
- `--source-script`.
- `--failure-detail-log` optional.
- `--root-cause-hint` optional.
- `--summary-outcome` optional.
- `--evidence-ref` optional.

Responsibilities:

- Validate `$DESIGN_TMPDIR` with `lib-design-tmpdir.sh`.
- Validate each token through:
  - `stall-recovery-report.sh --profile generic --artifact-prefix design-failure --implement-tmpdir "$DESIGN_TMPDIR" validate-token ...`
- Validate the completed candidate file through:
  - `stall-recovery-report.sh --profile generic --artifact-prefix design-failure --implement-tmpdir "$DESIGN_TMPDIR" validate-terminal-state --primary-state-file <candidate>`
- Reject raw prompt, issue, feature, plan, repo path, URL, and log-tail values.
- Accept `--failure-detail-log` only when it is under `$DESIGN_TMPDIR` and not a symlink.
- Write the strict `design-failure-terminal-state.env` contract.
- Preserve an existing terminal state unless explicitly invoked by the same terminal path with identical outcome.
- Emit quiet KVs to captured stdout only.
- Return non-zero on invalid input so callers can fail closed to fallback print.

### NEW: skills/design/scripts/design-stage-terminal-state.md

Document the staging helper.

- List inputs and outputs.
- Document required and optional KV fields.
- Document the shared validation API calls.
- Document path confinement and symlink rejection.
- Document redaction rules.
- Document intended callers:
  - Step 0b clarify hard halt.
  - Step 2b.5 decompose-panel retry exhaustion.
  - publish and postplan hard-fail paths when local writers delegate.

### NEW: skills/design/scripts/test-design-stage-terminal-state.sh

Add a hermetic harness.

Cover:

- Writes all required terminal-state keys.
- Stages `failed-clarify`.
- Stages `failed-judge-panel` from `SITE=decompose-panel`.
- Rejects unknown outcomes.
- Rejects unknown design vocab tokens.
- Calls shared `validate-token`.
- Calls shared `validate-terminal-state`.
- Rejects outside-tmpdir evidence paths.
- Rejects symlinked evidence paths.
- Does not include raw prompt, issue, feature, plan, repo path, URL, or log tail.
- Preserves an existing different terminal state.
- Emits KV-only stdout.

### NEW: skills/design/scripts/design-failure-report.sh

Create the /design teardown gate driver.

Inputs:

- `--design-tmpdir`.
- `--outcome`.
- `--repo` optional.
- `--issue` optional.
- `--run-id` optional.

Responsibilities:

- Validate `$DESIGN_TMPDIR` with `lib-design-tmpdir.sh`.
- Pass `--implement-tmpdir "$DESIGN_TMPDIR"` on every generic `stall-recovery-report.sh` invocation.
- Pass explicit generic state overrides on every terminal classify and terminal compose invocation:
  - `--primary-state-file "$DESIGN_TMPDIR/design-failure-terminal-state.env"`.
  - `--session-env-file "$DESIGN_TMPDIR/source-env.sh"`.
  - `--finalize-state-file "$DESIGN_TMPDIR/finalize-state.sh"` when present.
- Validate terminal state with `validate-terminal-state` before terminal `classify`.
- Enforce the explicit success allowlist:
  - `approved`.
  - `approved-partition`.
- Enforce sentinel precedence:
  - terminal sentinel first.
  - escalation-success sentinel second.
  - operator-action sentinel third.
- Normalize report decision:
  - terminal failure.
  - escalation-success.
  - operator-action skip.
  - skip.
- Accept failure outcomes:
  - `failed-plan-write`.
  - `failed-publish`.
  - `failed-postplan`.
  - `failed-clarify`.
  - `failed-judge-panel`.
  - `failed-publish-tail`.
  - existing cancelled outcomes.
- Read staged terminal state from `design-failure-terminal-state.env`.
- Read escalation evidence from the generic ledger files:
  - `design-failure-escalation-ledger.tsv`.
  - `design-failure-escalation-fallback.tsv`.
  - `design-failure-escalation-record-failure.env`.
  - tagged record-escalation Tool Failure entries.
- Treat Step 3 panel degradation as escalation evidence only.
- For terminal reports:
  - run terminal `classify` through the generic helper.
  - build deterministic root-cause files from cited local evidence.
  - compose and file the terminal report.
- For escalation-success reports:
  - check ledger or fallback evidence.
  - run `init-attempts` with zero history accepted.
  - build bounded deterministic root-cause evidence.
  - build the sensitive corpus.
  - call `compose-report --report-kind escalation-success`.
  - do not run terminal `classify`.
- Build deterministic root-cause files from cited local evidence:
  - terminal helper contract failures default to `larch-defect`.
  - publish transport/auth failures default to `environment`.
  - cancelled/operator paths default to `operator-action` and skip filing.
- Build Tier B sensitive corpus from design inputs:
  - `plan.txt`.
  - `composed-plan.md`.
  - `execution-issues.md`.
  - `issue-body.txt`.
  - `feature-description.txt`.
  - related raw feature or issue input artifacts under `$DESIGN_TMPDIR`.
  - validator logs.
  - design publish logs.
  - `source-env.sh`.
  - `session-env.sh` if present.
  - final summary.
  - run-log pointers.
- Compose and file through shared helper paths:
  - Tier A issue input in larch dev clones.
  - Tier B upstream filing elsewhere.
- Pass `design-failure-sensitive-corpus.env` to the cross-repo filing helper.
- Write one sentinel after terminal, escalation-success, or operator-action handling:
  - `design-failure-terminal-report.env`.
  - `design-failure-escalation-success.env`.
  - `design-failure-operator-action.env`.
- For operator-action skips:
  - write or repair `design-failure-operator-action-chat.md`.
  - write or repair the run-log audit or pointer.
  - never file.
- Emit quiet KVs for status and URL to captured stdout only.
- Never block final summary rendering if filing fails.
- Preserve `design-failure-chat-print.md` for `fallback-print-required`.
- Fail closed to fallback print when root-cause evidence is missing or Tier B validation rejects the body.

### NEW: skills/design/scripts/design-failure-report.md

Document the contract.

- List inputs and outputs.
- Define the terminal-state KV contract.
- Define terminal and escalation surfaces.
- Define supported failure outcomes.
- Define the success-outcome allowlist.
- Define sentinel precedence.
- Define Tier A and Tier B behavior.
- State that escalation-success mirrors implement Step 18a.5:
  - ledger evidence.
  - init attempts.
  - root-cause.
  - sensitive corpus.
  - `compose-report --report-kind escalation-success`.
  - no terminal `classify`.
- State that Tier B has no log tails in v1.
- State that raw design/user content is sensitive by default.
- State that `$DESIGN_TMPDIR/source-env.sh` is sensitive input.
- State that panel degradation is non-terminal in the current Step 3 flow.
- State that Step 2b.5 decompose-panel retry exhaustion is terminal.
- State that operator-action skips always write `design-failure-operator-action-chat.md` and run-log audit records.
- State that helper invocations pin `--implement-tmpdir "$DESIGN_TMPDIR"`.
- State that terminal classify and compose use explicit generic state overrides.
- State that terminal state is revalidated with the shared generic validation API.

### NEW: skills/design/scripts/test-design-failure-report.sh

Add a hermetic harness.

Cover:

- skip on `cancelled-*`.
- operator-action root cause skips filing and writes local, chat, and run-log records.
- existing operator-action sentinel still repairs missing chat sidecar.
- approved outcome with ledger plus operator-action sentinel skips filing.
- terminal report for `failed-plan-write`.
- terminal report for `failed-publish`.
- terminal report for staged `failed-postplan`.
- terminal report for `failed-clarify` after staged terminal state exists.
- terminal report for `failed-judge-panel`.
- terminal report for publish-tail hard halt.
- terminal wins over escalation ledger on failed outcome.
- success allowlist admits `approved` and `approved-partition`.
- success allowlist rejects cancelled, failed, unknown, and missing outcomes.
- existing terminal, escalation-success, and operator-action sentinels prevent duplicate filing.
- escalation-success files on approved outcome with ledger.
- escalation-success does not run terminal `classify`.
- no escalation-success without ledger.
- `postplan-operator-required` ledger can produce escalation-success only after an approved outcome.
- panel degradation evidence on approved outcome is escalation evidence, not terminal evidence.
- panel degradation evidence on cancelled or failed outcome does not file escalation-success.
- Tier B fallback preserves chat-print.
- Tier B sensitive corpus rejects leaked `issue-body.txt` and `feature-description.txt` content.
- Tier B sensitive corpus rejects leaked `source-env.sh` content.
- dry-run avoids network.
- symlink and outside-tmpdir state files fail closed.
- every generic helper call receives `--implement-tmpdir "$DESIGN_TMPDIR"`.
- terminal classify works from terminal state without any `ship-pr-state.sh`.
- invalid terminal state fails closed before `classify`.

### NEW: skills/design/scripts/test-design-failure-report.md

Document the harness scope and stubs.

### UPDATED: skills/design/scripts/render-final-summary.sh

Wire the gate in the post phase without breaking stdout.

- Run the report gate only in `--post-publish-only`.
- Accept new failed outcomes:
  - `failed-postplan`.
  - `failed-clarify`.
  - `failed-judge-panel`.
  - `failed-publish-tail`.
- Call `design-failure-report.sh` after initial issue-count refresh and before final `render_or_fallback`.
- Capture helper stdout and stderr into `$DESIGN_TMPDIR` sidecars.
- Do not allow helper KVs to enter `final-summary.md` stdout.
- If helper appends a warning to `execution-issues.md`, refresh issue counts and rerun `render_or_fallback`.
- Print `final-summary.md` only after counts are fresh.
- Upsert tracking issue summary after printing-ready content is rendered.
- If `fallback-print-required`, print sanitized `design-failure-chat-print.md` outside the final-summary body.
- If `design-failure-operator-action-chat.md` exists, print it outside the final-summary body.
- Pass `--outcome`, `--repo`, `--issue`, and `--run-id`.
- Append report status to `execution-issues.md` only on helper failure.
- Preserve the existing stdout contract that stdout equals `final-summary.md`, except for explicit fallback and operator-action chat-print blocks after the summary.

### UPDATED: skills/design/scripts/render-final-summary.md

Document the teardown-gate output contract.

- Document that the report gate runs only in post phase.
- Document the new failed outcomes.
- Document captured helper stdout and stderr sidecars.
- State that helper KVs never enter `final-summary.md`.
- State that fallback chat-print is emitted after the summary body.
- State that operator-action chat audit is emitted after the summary body whenever the sidecar exists.

### UPDATED: skills/design/scripts/design-publish.sh

Stage hard failures that currently abort before the normal outcome path.

- Before `fail` exits for publish-tail hard failures, write `design-failure-terminal-state.env` when `$DESIGN_TMPDIR` is valid.
- For plan-block write failure, stage terminal state before invoking final summary.
- For publish failure after plan write, stage terminal state before final summary.
- Use `design-stage-terminal-state.sh` or the same validated writer logic.
- Write the terminal-state KV contract with outcome, step, phase, site, trigger, bail reason, exit code, source script, and validated failure detail log.
- Preserve existing result env keys.
- Do not change the `PLAN_WRITE_OK` and `PUBLISH_OK` contracts.

### UPDATED: skills/design/scripts/design-publish.md

Document terminal-state staging.

- Document staged outcomes for plan-write and publish failures.
- Document the terminal-state KV keys written by the script.
- Document that existing result env keys remain unchanged.

### UPDATED: skills/design/scripts/design-step5c.sh

Handle publish-tail hard exits.

- When `_publish_rc` is `2` or unexpected, stage terminal state if not already staged.
- Write the terminal-state KV contract with `FAILURE_OUTCOME=failed-publish-tail`.
- Invoke `render-final-summary.sh --post-publish-only --outcome failed-publish-tail` before aborting when safe.
- Preserve current behavior for rc `0`, `1`, `3`, and `4`.

### UPDATED: skills/design/scripts/design-step5c.md

Document publish-tail reporting behavior.

- Document which publish return codes stage terminal state.
- Document `failed-publish-tail` final-summary routing.
- Document unchanged rc `0`, `1`, `3`, and `4` behavior.

### UPDATED: skills/design/scripts/design-step3-review.sh

Route only true Step 3 hard failures through the report gate.

- Before hard-failing on `postplan-failed`, write `design-failure-terminal-state.env`.
- Do **not** invoke `render-final-summary.sh` from this script.
- Keep stdout as machine KVs only.
- Let prompt-side orchestration set `SUMMARY_OUTCOME=failed-postplan` and run the existing Final summary block after reading Step 3 KVs.
- Make `design-step3-review.sh` the single owner for Step 3 escalation recording.
- Explicitly branch escalation recording on `STEP3_REVIEW_LOOP_STATUS` before any `LOOP_STATUS` remap to `complete`.
- For `main-agent-vote-required`, `main-agent-apply-required`, and `postplan-operator-required`:
  - record escalation durably via generic `record-escalation`.
  - pass `--profile generic --artifact-prefix design-failure --implement-tmpdir "$DESIGN_TMPDIR"`.
  - pass `--session-env-file "$DESIGN_TMPDIR/source-env.sh"` when supported.
  - capture helper stdout/stderr into sidecars.
  - never interleave helper output with Step 3 KV stdout.
- For `panel-failed`, `tally-error`, and `degraded-empty-collector`:
  - do not stage terminal state.
  - do not invoke a failed-panel summary.
  - preserve current Gate B bypass behavior.
  - record escalation/degradation evidence when the status represents script-owned review degradation.
- Do not handle Step 2b.5 decompose-panel retry exhaustion in this script.
- Preserve existing exit codes and operator-visible failure behavior after the gate runs.
- Do not file more than once if a sentinel already exists.

### UPDATED: skills/design/scripts/design-step3-review.md

Document Step 3 reporting behavior.

- State that Step 3 stdout is KV-only.
- State that `design-step3-review.sh` owns Step 3 escalation recording.
- State that prompt-side orchestration must not call `record-escalation` for Step 3 statuses already recorded by this script.
- State that recording branches on `STEP3_REVIEW_LOOP_STATUS` before `LOOP_STATUS` remap.
- State that `postplan-failed` stages terminal state but does not render final summary in-script.
- State that the orchestrator owns `failed-postplan` final-summary routing.
- Document durable escalation recording for:
  - `main-agent-vote-required`.
  - `main-agent-apply-required`.
  - `postplan-operator-required`.
  - panel degradation statuses.
- State that panel degradation is non-terminal.
- State that Step 2b.5 decompose-panel retry exhaustion is outside this script and is owned by Split-path orchestration.

### UPDATED: skills/design/scripts/design-step-validator-autofix.sh

Record validator escalation when autofix does not resolve defects.

- After `_autofix_status` normalizes.
- For `exhausted`, `failed`, `unavailable`, and `skipped-cycle-cap`, call:
  - `stall-recovery-report.sh --profile generic --artifact-prefix design-failure --implement-tmpdir "$DESIGN_TMPDIR" record-escalation ...`
- Pass `--session-env-file "$DESIGN_TMPDIR/source-env.sh"` when supported.
- Map site strings to stable generic-profile design tokens.
- Include the original validator log as `--failure-detail-log` only when it is under `$DESIGN_TMPDIR`.
- Reject symlinked and outside-tmpdir logs through the generic helper.
- Capture helper stdout/stderr into sidecars.
- Do not block the existing operator prompt if recording degrades.
- When the operator chooses **Cancel**:
  - write `design-failure-operator-action.env`.
  - write `design-failure-operator-action-chat.md`.
  - write the redacted run-log audit or pointer.
  - ensure later approved teardown cannot file escalation-success from the earlier ledger.

### UPDATED: skills/design/scripts/design-step-validator-autofix.md

Document validator escalation recording.

- Document the autofix statuses that record escalation.
- Document generic helper arguments.
- Document log path confinement.
- Document non-blocking degradation behavior.
- Document validator Cancel as operator-action with sentinel, chat sidecar, and run-log audit writes.

### UPDATED: skills/design/references/decompose-panel.md

Move retry-exhaustion reporting to the Step 2b.5 owner.

- Replace the second `PANEL_STATUS=panel-failed` hard exit with staged terminal handling.
- On first `panel-failed`, keep **Retry panel** / **Cancel**.
- On second `panel-failed`:
  - invoke `design-stage-terminal-state.sh`.
  - use `--outcome failed-judge-panel`.
  - use `--step judge-panel`.
  - use `--phase judge-panel`.
  - use `--site decompose-panel`.
  - use `--trigger decompose-panel-retry-exhausted`.
  - use a stable bail reason.
  - use `--source-script split-path`.
  - export `SUMMARY_OUTCOME=failed-judge-panel`.
  - run the existing Final summary block.
  - exit `/design` 1.
  - preserve `$DESIGN_TMPDIR`.
- If staging fails, continue to the same Final summary block so the report gate can fail closed to fallback print.
- Keep Split-path stdout and operator text free of helper KV leakage.
- Update terminal outcomes to list retry exhaustion as final-summary-routed failure.

### UPDATED: skills/design/SKILL.md

Add prompt-side orchestration instructions.

- Define /design terminal and escalation report surfaces.
- Define the success allowlist for escalation-success:
  - `approved`.
  - `approved-partition`.
- Define the sentinel precedence used by the teardown gate.
- Add new final-summary outcomes to every `SUMMARY_OUTCOME` enumeration:
  - `failed-clarify`.
  - `failed-postplan`.
  - `failed-judge-panel`.
  - `failed-publish-tail`.
- In the Final summary block contract:
  - include Step 2b.5 retry exhaustion among Split-path terminal branches that run the block.
  - state that `failed-judge-panel` is emitted by Split-path on second decompose-panel `panel-failed`.
- In Step 0b clarify handling:
  - invoke `design-stage-terminal-state.sh` before unrecovered clarify hard exits.
  - set `SUMMARY_OUTCOME=failed-clarify` after staging succeeds or fails closed.
  - run the existing final-summary block with `failed-clarify`.
  - treat clarify operator cancel as `operator-action`.
  - keep successful clarify response behavior as `cancelled-clarify`.
  - do not reference or call a non-existent `design-step-clarify.sh`.
- In Step 2b.5 Split-path:
  - on second `PANEL_STATUS=panel-failed`, stage `failed-judge-panel`.
  - run the existing Final summary block before exit 1.
  - do not delegate this path to `design-step3-review.sh`.
- In Step 3 branch matrix:
  - state that `design-step3-review.sh` owns Step 3 escalation recording.
  - forbid prompt-side `record-escalation` for `main-agent-vote-required`, `main-agent-apply-required`, `postplan-operator-required`, and panel degradation statuses.
  - keep orchestrator steps limited to MainAgent vote, MainAgent apply, postplan operator work, and final-summary routing.
  - when `postplan-failed` is read from the Step 3 KV result, set `SUMMARY_OUTCOME=failed-postplan` and run the existing Final summary block from the orchestrator.
  - do not have `design-step3-review.sh` render final-summary prose on its KV stdout channel.
  - keep `panel-failed`, `tally-error`, and `degraded-empty-collector` as non-terminal Gate B bypass statuses.
  - record panel degradation as warning/escalation evidence only from the script owner.
- In the shared validator failure section:
  - state that non-ok autofix statuses record escalation before the operator prompt.
  - state that operator **Cancel** writes the operator-action sentinel, chat sidecar, and run-log audit, then does not file.
- In Step 5c:
  - describe hard publish-tail exit staging and `failed-publish-tail` summary routing.
- In final-summary contract:
  - note that `render-final-summary.sh --post-publish-only` runs the report gate before final render and upsert.
  - note that fallback chat-print is emitted outside the final-summary body.
  - note that operator-action chat audit is emitted outside the final-summary body.

### UPDATED: scripts/test-design-structure.sh

Add static contract coverage for prompt-side clarify, Split-path, and Step 3 routing.

- Assert Step 0b clarify hard-fail prose invokes `design-stage-terminal-state.sh`.
- Assert Step 0b clarify hard-fail prose stages `failed-clarify`.
- Assert Step 0b clarify operator cancel remains operator-action or `cancelled-clarify`.
- Assert Step 2b.5 second decompose-panel `panel-failed` stages `failed-judge-panel`.
- Assert Step 2b.5 second decompose-panel `panel-failed` runs the Final summary block before exit 1.
- Assert Step 2b.5 owns decompose-panel retry exhaustion.
- Assert `failed-clarify`, `failed-postplan`, `failed-judge-panel`, and `failed-publish-tail` appear in `SUMMARY_OUTCOME` enumerations.
- Assert `skills/design/scripts/design-step-clarify.sh` is not referenced as an existing script.
- Assert Step 3 `postplan-failed` is routed through prompt-side final-summary orchestration, not in-script summary printing.
- Assert Step 3 prompt-side prose does not call `record-escalation` for statuses owned by `design-step3-review.sh`.
- Assert Step 3 panel degradation statuses are described as non-terminal.
- Assert Step 3 does not claim ownership of Step 2b.5 decompose-panel retry exhaustion.
- Assert `postplan-failed` is the Step 3 terminal hard-fail report path.
- Assert `postplan-operator-required` is listed as an escalation trigger.

### UPDATED: skills/design/scripts/test-render-final-summary.sh

Add teardown-gate coverage.

- Stub `design-failure-report.sh`.
- Assert it runs only in post phase.
- Assert it runs before summary upsert.
- Assert helper stdout and stderr are captured.
- Assert helper KVs do not appear in `final-summary.md`.
- Assert helper failures append a warning and do not prevent final summary printing.
- Assert warning counts refresh after helper warning append.
- Assert fallback-print-required prints `design-failure-chat-print.md` outside the summary body.
- Assert operator-action sidecar prints outside the summary body.
- Assert pre phase does not run the gate.
- Assert `failed-postplan`, `failed-clarify`, `failed-judge-panel`, and `failed-publish-tail` are accepted.

### UPDATED: skills/design/scripts/test-design-publish.sh

Add publish staging coverage.

- Plan-write failure creates terminal state.
- Publish failure creates terminal state.
- Hard fail creates terminal state when possible.
- Terminal state includes required KV keys.
- Existing result env behavior remains unchanged.

### NEW: skills/design/scripts/test-design-step3-review.sh

Add Step 3 report-gate coverage.

- `postplan-failed` stages terminal state.
- `postplan-failed` does not invoke `render-final-summary.sh`.
- `postplan-failed` stdout remains KV-only.
- `main-agent-vote-required` records escalation.
- `main-agent-apply-required` records escalation.
- `postplan-operator-required` records escalation.
- Escalation recording branches on `STEP3_REVIEW_LOOP_STATUS`, not remapped `LOOP_STATUS`.
- Escalation helper output is captured and does not pollute Step 3 KV stdout.
- `panel-failed` does not stage terminal state.
- `tally-error` does not stage terminal state.
- `degraded-empty-collector` does not stage terminal state.
- Panel degradation records warning or escalation evidence only.
- Existing Gate B bypass behavior is preserved for panel degradation.
- Step 2b.5 decompose-panel retry exhaustion is not handled here.
- Existing sentinels prevent duplicate filing.

### NEW: skills/design/scripts/test-design-step3-review.md

Document the harness scope and stubs.

### UPDATED: skills/design/scripts/test-decompose-panel-dispatch.sh

Add Split-path owner coverage where the harness can model orchestration stubs.

- Keep existing dispatcher `PANEL_STATUS=panel-failed` assertions.
- Add a stubbed Split-path retry-exhaustion scenario if the harness already wraps the orchestration contract.
- Assert second `panel-failed` maps to `failed-judge-panel` staging in the Split-path owner.
- If the harness cannot cover prompt orchestration, document that `scripts/test-design-structure.sh` owns this static coverage.

### UPDATED: skills/design/scripts/test-decompose-panel-dispatch.md

Document any added retry-exhaustion harness scope, or state that static structure tests cover prompt-owned retry exhaustion.

### UPDATED: Makefile

Add harness targets.

- `test-design-stage-terminal-state`.
- `test-design-failure-report`.
- `test-design-step3-review`.
- Include `test-file-failure-report-cross-repo` if not already exposed.
- Include `scripts/test-design-structure.sh` in the existing design-structure target if needed.
- Keep `test-decompose-panel-dispatch` exposed for Split-path dispatcher coverage.

### UPDATED: scripts/relevant-checks.sh

Map new and changed files to focused harnesses.

- Map terminal staging helper files to `test-design-stage-terminal-state`.
- Map design-failure-report files to `test-design-failure-report`.
- Map Step 3 review changes to `test-design-step3-review`.
- Map `skills/design/references/decompose-panel.md` and Split-path `SKILL.md` changes to `scripts/test-design-structure.sh` and `test-decompose-panel-dispatch` when applicable.
- Map `skills/design/SKILL.md` clarify/reporting changes to `scripts/test-design-structure.sh`.
- Map cross-repo filing helper changes to `test-file-failure-report-cross-repo`.
- Include changed stall-report files in existing stall-report harness selection.
- Include render-final-summary and publish changes in their existing harness selections.
- Include changed sibling `.md` contracts in the same relevant harness mappings.

### UPDATED: docs/linting.md

Document the new harnesses and relevant-checks mapping.

- `test-design-stage-terminal-state`.
- `test-design-failure-report`.
- `test-design-step3-review`.
- Design-structure coverage for clarify/reporting prose.
- Split-path decompose-panel retry-exhaustion coverage.
- Cross-repo filing helper coverage for design-prefix Tier B.
- Stall-report generic-profile coverage.

### UPDATED: docs/configuration-and-permissions.md

Document /design auto error reporting.

Include:

- Tier A and Tier B behavior.
- Cross-repo filing.
- Dry-run behavior.
- Fallback-print-required behavior.
- One issue per run.
- Operator-action skip.
- Operator-action chat and run-log audit.
- Success-outcome allowlist for escalation-success.
- Panel degradation as non-terminal evidence.
- Step 2b.5 decompose-panel retry exhaustion as terminal `failed-judge-panel`.
- Step 3 main-agent and postplan-operator escalation evidence.
- Tier B sensitive content rules for design plans, issue bodies, feature descriptions, paths, repo names, URLs, logs, and `source-env.sh`.

### UPDATED: docs/workflow-lifecycle.md

Add the /design teardown reporting step.

- Mention terminal-failure and escalation-success reports.
- State that hard-fail paths route through the same one-issue gate before abort when safe.
- State that Step 3 `postplan-failed` routes through prompt-side final-summary orchestration to avoid KV stdout pollution.
- State that Step 0b clarify hard halts mechanically stage terminal state before final summary.
- State that Step 2b.5 decompose-panel retry exhaustion is terminal and routes through Split-path final-summary orchestration.
- State that ordinary Step 3 panel degradation continues the run.
- State that normal successful runs without escalation do not file.
- State that operator-action skips are audited in chat and run logs but not filed.
- State that panel degradation continues the run and may become escalation-success evidence only after an approved outcome.

### UPDATED: docs/run-logs.md

Document new design failure artifacts.

- `design-failure-*.env`.
- `design-failure-*.md`.
- escalation ledgers.
- fallback chat print.
- operator-action audit artifacts.
- sentinels.
- captured helper stdout/stderr sidecars.
- terminal-state KV contract artifacts.

### UPDATED: SECURITY.md

Add the /design reporting security boundary.

- /design Tier A and Tier B surfaces.
- Tier B has bounded narrative and no log tails.
- Raw design plan text, issue bodies, feature text, logs, paths, repo names, URLs, and `source-env.sh` are sensitive.
- Generic helper path confinement applies to `$DESIGN_TMPDIR`.
- All generic helper calls from /design pin `--implement-tmpdir "$DESIGN_TMPDIR"`.
- Cross-repo filing can publish to upstream larch under the operator identity.
- Panel degradation is non-terminal in current /design Step 3 flow and must not leak raw review artifacts into Tier B.
- Step 2b.5 decompose-panel retry exhaustion is terminal and must still use bounded, redacted Tier B evidence.
- Residual risk: deterministic root-cause templates may misclassify nuanced failures.

## Edge cases

- **Both terminal and escalation evidence exist on failed outcome**: file terminal only.
- **Both terminal and escalation evidence exist on successful outcome**: do not honor stale terminal state; file escalation only when success allowlist and evidence pass.
- **Cancelled outcome with ledger**: skip filing and record operator-action locally, in chat, and in the run log.
- **Validator Cancel after escalation ledger**: operator-action sentinel wins and prevents escalation-success on later approved teardown.
- **Panel degradation with later approval**: file escalation-success only if evidence exists and Tier rules pass.
- **Panel degradation with cancellation or failure**: do not file escalation-success.
- **Step 2b.5 decompose-panel retry exhaustion**: stage `failed-judge-panel`, run final summary, and file terminal when Tier rules pass.
- **MainAgent vote/apply with later approval**: file escalation-success only if durable ledger evidence exists and Tier rules pass.
- **Postplan operator escalation with later approval**: file escalation-success only if durable ledger evidence exists and Tier rules pass.
- **Missing root-cause evidence**: fail closed to fallback print, no public issue.
- **Missing terminal-state required KV**: fail closed to fallback print, no public issue.
- **Invalid shared validation result**: fail closed to fallback print, no public issue.
- **Tier B sensitive-token hit**: fallback print only.
- **Cross-repo helper failure**: fallback print only.
- **Fallback-print-required**: print sanitized `design-failure-chat-print.md` outside the final-summary body.
- **Operator-action sidecar present**: print sanitized `design-failure-operator-action-chat.md` outside the final-summary body.
- **Dry run**: write artifacts, do not call GitHub.
- **Symlinked staged files**: reject and append a redacted warning.
- **Outside-tmpdir evidence paths**: reject and append a redacted warning.
- **Repeated teardown invocation**: sentinels prevent duplicate filing.
- **Hard-fail abort before Step 5c**: stage terminal state and run the gate directly or through post-phase final summary before exit when safe.
- **Postplan hard fail**: Step 3 script stages state and returns KVs only; prompt-side orchestration runs final summary.
- **Clarify hard halt**: Step 0b invokes `design-stage-terminal-state.sh` for `failed-clarify` and uses the existing final-summary path, not a new `design-step-clarify.sh`.
- **Step 3 status remap**: escalation recording reads `STEP3_REVIEW_LOOP_STATUS` before `LOOP_STATUS` is rewritten.

## Failure modes

- Generic helper regression could alter /implement reports.
  - Mitigate with byte-stability tests for default filenames, titles, and signatures.
- Generic classification could accidentally depend on `ship-pr-state.sh`.
  - Mitigate with terminal-state-only generic classify tests.
- Shared validation API could drift from classification vocab.
  - Mitigate with `validate-token`, `validate-terminal-state`, and generic classify tests using the same design tokens.
- Escalation-success could accidentally use terminal classify.
  - Mitigate with tests that assert ledger-based `compose-report --report-kind escalation-success`.
- Design terminal-state staging could omit required KVs.
  - Mitigate with contract validation and staging tests.
- Clarify hard-fail handling could remain prompt-only.
  - Mitigate with `design-stage-terminal-state.sh` harness coverage and structure tests.
- Design token vocab could be added to the wrong parity surface.
  - Mitigate by keeping design tokens in generic-profile safe-value helpers and leaving Tier B field allowlists unchanged unless new fields are exposed.
- Cross-repo Tier B filing could use the wrong sensitive corpus.
  - Mitigate with explicit `--sensitive-corpus-file`, `source-env.sh` corpus tests, and design-prefix dedup tests.
- Report gate could pollute final-summary stdout.
  - Capture helper stdout/stderr and keep KVs out of `final-summary.md`.
- Operator-action audit could be written but not shown to the operator.
  - Mitigate by always printing `design-failure-operator-action-chat.md` after the summary body when present.
- Step 3 could pollute KV stdout with summary prose.
  - Stage terminal state in the script and let prompt-side orchestration run the final-summary block.
- Step 3 escalations could duplicate ledger rows.
  - Make `design-step3-review.sh` the only owner and forbid prompt-side `record-escalation` for those statuses.
- Step 3 main-agent or operator escalations could be missed after status remap.
  - Branch on `STEP3_REVIEW_LOOP_STATUS` before `LOOP_STATUS` remap.
- Report gate could make warning counts stale.
  - Run before final render and refresh counts after any warning append.
- Hard publish or postplan exits may not have enough context.
  - Stage best-effort state before abort and cite local helper evidence.
- Operator-action skips could disappear from durable audit.
  - Write redacted chat-visible and run-log records.
- Panel degradation could be misclassified as terminal.
  - Mitigate with Step 3 tests that assert no terminal state is staged for `panel-failed`, `tally-error`, or `degraded-empty-collector`.
- Step 2b.5 decompose-panel retry exhaustion could be lost because the wrong owner handles it.
  - Mitigate with `decompose-panel.md`, `SKILL.md`, and structure tests asserting Split-path stages `failed-judge-panel` and runs final summary.
- Clarify hard-fail handling could target a non-existent script.
  - Mitigate with structure tests that assert Step 0b owns clarify staging and no `design-step-clarify.sh` reference is introduced.
- Behavior-changing script docs could drift.
  - Update sibling `.md` contracts with the script changes.

## Testing strategy

Run focused tests first:

- `bash skills/implement/scripts/test-stall-recovery-report.sh`
- `bash scripts/test-file-failure-report-cross-repo.sh`
- `bash skills/design/scripts/test-design-stage-terminal-state.sh`
- `bash skills/design/scripts/test-design-failure-report.sh`
- `bash skills/design/scripts/test-render-final-summary.sh`
- `bash skills/design/scripts/test-design-publish.sh`
- `bash skills/design/scripts/test-design-step3-review.sh`
- `bash skills/design/scripts/test-decompose-panel-dispatch.sh`
- `bash skills/design/scripts/test-design-step2b-drafter.sh`
- `bash skills/design/scripts/test-review-design-step3-loop.sh`
- `bash scripts/test-design-structure.sh`

Then run repository checks:

- `bash scripts/relevant-checks.sh`
- `make lint`

diff_added: 1990
diff_deleted: 230
diff_lines: 2220

## Acceptance

- All /implement defaults remain byte-compatible.
- At most one report is filed per /design run.
- Cancelled runs do not file; operator-action is audited in chat and run logs.
- Terminal failures win over escalation-success on failed outcomes.
- `render-final-summary.sh` remains KV-stdout-clean; helper output is captured.
- Panel degradation is non-terminal; decompose-panel retry exhaustion is terminal.
- All generic helper calls from /design pin `--implement-tmpdir "$DESIGN_TMPDIR"`.

diff_lines: 2220

## Test plan
(no test plan section in plan-file)
