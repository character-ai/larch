### FINDING_1: Hard-fail paths exit before the teardown report gate runs
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Codex-dyn-core-contract, Codex-dyn-core-contract, Cursor-dyn-design-teardown-risk, Codex-dyn-design-teardown-risk
- **Severity**: important
- **Concern**: The plan stages terminal failure state (e.g. `failed-postplan` / `STEP3_REVIEW_LOOP_STATUS=postplan-failed`) and wires `design-failure-report.sh` only through `render-final-summary.sh --post-publish-only`, but several hard-fail branches exit before Step 5c / final summary (notably `postplan-failed` in `design-step3-review.sh`, and similarly decompose-panel second `panel-failed`). Staged `design-failure-terminal-state.env` alone does not file a report; `render-final-summary.sh` never runs on those paths, and the outcome enum does not yet accept `failed-postplan`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add a postplan-failed abort contract: export a new SUMMARY_OUTCOME (e.g. failed-postplan), run design-step-final-summary.sh or render-final-summary --post-publish-only, then exit; extend render-final-summary outcome enum and design-failure-report normalization to accept it
  - From Codex-Arch: Run the report gate on each staged hard-fail path before exit, or route those paths through a failed-* final-summary outcome that invokes design-failure-report; cover the new outcome in the design-failure-report harness
  - From Cursor-Innovation: (same theme as Codex-Innovation below — postplan terminal path)
  - From Codex-Innovation: Add the minimal terminal path for `postplan-failed`: stage state, run the report gate or final-summary wrapper with a supported failure outcome, then abort.
  - From Cursor-Pragmatic: Add `skills/design/scripts/design-step3-review.sh` (and contract doc) to the plan: before the postplan-failed exit, write `design-failure-terminal-state.env`, invoke `design-failure-report.sh` best-effort, then exit; or run the Final summary fence with a dedicated failure outcome that still reaches the report gate
  - From Codex-Pragmatic: For each terminal hard-fail path, either call design-failure-report.sh directly before exit or render-final-summary with an added failure outcome. Include the decompose panel retry-exhaustion surface if it remains terminal.
  - From Cursor-Requirements: Mirror the `design-step5c.sh` hard-exit pattern: stage `design-failure-terminal-state.env`, invoke `render-final-summary.sh` (or `design-failure-report.sh`) with a failure outcome, then abort; add harness coverage for this abort path
  - From Codex-Requirements: Add a supported teardown path for `postplan-failed`: either run `design-failure-report.sh` before the hard fail or add a `failed-postplan` final-summary outcome and invoke the post-phase gate; update the enum and the render/SKILL tests for that path
  - From Codex-dyn-core-contract: Update the plan so the postplan-failed branch runs the report gate before exit. Add failed-postplan to the final-summary outcome contract or call design-failure-report.sh directly on that abort path. Cover it in test-design-failure-report.sh and test-render-final-summary.sh.
  - From Cursor-dyn-design-teardown-risk: On `postplan-failed`, invoke the same teardown gate (direct `design-failure-report.sh` or `render-final-summary.sh --post-publish-only` with a new enumerated outcome) after staging `design-failure-terminal-state.env`, before exit.
  - From Codex-dyn-design-teardown-risk: Update the Step 3 `postplan-failed` branch to run the teardown gate before abort, either through `render-final-summary.sh` with a new `failed-postplan` enum or a direct `design-failure-report.sh` call. Add `failed-postplan` to render-final-summary outcome tests.


### FINDING_2: Cross-repo Tier B dedup helper is still stall-recovery–specific
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Codex-Pragmatic, Codex-dyn-core-contract, Cursor-dyn-tier-b-security, Codex-dyn-tier-b-security
- **Severity**: important
- **Concern**: `file-failure-report-cross-repo.sh` hard-codes `stall-recovery-sensitive-corpus.env`, calls `validate-tier-b-public-file` with implement defaults, and raw-body rejection recognizes only `/implement` report headings. With `design-failure-*` artifacts, duplicate `/design` Tier B reports fall back instead of posting dedup occurrence comments, and comment validation can use the wrong or missing corpus.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add a minimal generic prefix or --sensitive-corpus-file path to file-failure-report-cross-repo.sh and pass it from the generic compose path; update the raw-body guard to reject both /implement and /design report headings
  - From Codex-Innovation: Teach the filing helper to accept a sensitive-corpus path or artifact prefix, and pass the design corpus from `design-failure-report.sh`.
  - From Codex-Pragmatic: Add the minimum parameter needed by file-failure-report-cross-repo.sh, such as sensitive-corpus file plus generic profile/artifact-prefix, and pass it from design-failure-report.sh. Keep /implement defaults unchanged.
  - From Codex-dyn-core-contract: Add scripts/file-failure-report-cross-repo.sh and scripts/test-file-failure-report-cross-repo.sh to the plan. Pass or discover the prefixed sensitive corpus and validator profile from compose-report. Add a design-prefix Tier B dedup test in test-stall-recovery-report.sh or test-file-failure-report-cross-repo.sh.
  - From Cursor-dyn-tier-b-security: Add ### UPDATED: scripts/file-failure-report-cross-repo.sh with --sensitive-corpus-file (default stall-recovery-sensitive-corpus.env); pass design-failure-sensitive-corpus.env from prefix-aware compose-report; extend test-file-failure-report-cross-repo.sh for design prefix
  - From Codex-dyn-tier-b-security: Add the minimum generic hook to the cross-repo helper, such as an explicit sensitive-corpus file argument, and pass the design-failure corpus from generic compose-report.


### FINDING_3: Tier B fallback report has no chat emission path
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: The plan preserves `design-failure-chat-print.md` and keeps the helper quiet, while `render-final-summary.sh` prints only `final-summary.md`. When cross-repo filing returns `fallback-print-required`, the required sanitized manual-filing report is not shown to the operator.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Print the sanitized design-failure-chat-print.md on fallback-print-required outside the final-summary body, matching the existing /implement Tier B fallback contract


### FINDING_4: Report-gate placement can leave stale warning counts and break stdout contract
- **Reviewer(s)**: Cursor-Innovation, Codex-Pragmatic, Codex-dyn-design-teardown-risk
- **Severity**: important
- **Concern**: The plan calls `design-failure-report.sh` after `render_or_fallback`, but warning/issue counts are refreshed and baked into `final-summary.md` earlier. If the gate appends to `execution-issues.md` or emits KVs after render, chat and upserted summaries can show stale Warning bullets; uncaptured helper stdout can also violate the existing “stdout equals final-summary.md” contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Call design-failure-report after the initial refresh_issue_counts and before render_or_fallback; re-run refresh_issue_counts if the helper appends to execution-issues.md
  - From Codex-Pragmatic: After appending a report-gate warning, refresh counts and rerender before printing and upsert, or run the gate before the final render path.
  - From Codex-dyn-design-teardown-risk: Call the gate with stdout/stderr captured to `$DESIGN_TMPDIR` sidecars. If it appends an execution-issues warning, refresh counts and rerun `render_or_fallback` before print/upsert. Extend `test-render-final-summary.sh` with a stub that emits KVs and fails, then assert stdout still matches `final-summary.md` and Warnings reflects the appended warning.


### FINDING_5: Required terminal surfaces omit clarify-loop and judge-panel collapse mappings
- **Reviewer(s)**: Codex-Innovation, Codex-Requirements
- **Severity**: important
- **Concern**: The binding scope requires enumerating terminal halts after internal retries, including clarify-loop exhaustion and judge-panel collapse, but the plan only names publish, plan-write, postplan, and publish-tail hard failures. Existing panel-failed / tally-error / degraded-empty-collector and clarify-related halt paths can still terminate without staged terminal report state or an explicit no-path mapping.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add only the existing required surfaces to the design failure surface: clarify branch unrecovered failures and Step 3 panel-collapse terminals such as `panel-failed`, `tally-error`, or `degraded-empty-collector`, with the intended report or operator-action mapping.
  - From Codex-Requirements: Map each required named surface to existing /design outcomes; stage and report every terminal mapping through the same one-issue gate, or explicitly state when a named surface has no current /design execution path


### FINDING_6: Design Tier B sensitive corpus omits raw issue and feature input artifacts
- **Reviewer(s)**: Codex-Innovation, Codex-Requirements
- **Severity**: important
- **Concern**: `issue-body.txt`, `feature-description.txt`, and related raw user design content are not in the proposed Tier B sensitive corpus. Bounded Tier B title or root-cause prose could quote issue-specific text without validator rejection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add those existing design input artifacts to the `design-failure-report.sh` sensitive corpus before Tier B validation.
  - From Codex-Requirements: Add `feature-description.txt` and `issue-body.txt` to the design Tier B sensitive corpus, and cover that leak path in the new design-failure-report harness


### FINDING_9: Design driver does not pin `--implement-tmpdir` on generic helper calls
- **Reviewer(s)**: Cursor-dyn-tier-b-security
- **Severity**: important
- **Concern**: `design-failure-report.sh` validates `DESIGN_TMPDIR` via `lib-design-tmpdir.sh`, but the plan does not require passing that same path as `--implement-tmpdir` on every `stall-recovery-report.sh` invocation. `record-escalation`, compose-report path confinement, and symlink rejection depend on that binding.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-tier-b-security: Document and implement that all generic helper invocations from design-failure-report and design-step-validator-autofix.sh pass --implement-tmpdir "$DESIGN_TMPDIR" after larch_design_tmpdir_validate; add harness cases for outside-tmpdir and symlinked --failure-detail-log rejection


### FINDING_10: `operator-action` skips lack required chat and run-log audit
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: Requirement 4 says `operator-action` skips filing but must record in chat and the run log. The plan only promises skip/local record behavior, so validator Cancel or an operator-action root cause can leave no durable run-log or chat audit trail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add a redacted operator-action record to the design run log and a chat-visible summary artifact or final-summary note when filing is skipped for operator action; assert this in the design-failure-report tests


### FINDING_11: Design step/phase/site tokens need vocab overrides, not allowlists.tsv alone
- **Reviewer(s)**: Cursor-dyn-core-contract
- **Severity**: important
- **Concern**: The plan implies design ledger tokens can be admitted by editing `stall-recovery-report-allowlists.tsv`, but that TSV only defines Tier B chat-print field schemas. Enum tokens are enforced in `safe_step_value` / `safe_site_value` / `safe_trigger_value` / `safe_phase_value`; TSV edits alone do not enable design escalation recording and can break cmd_lint triple parity without adding vocab.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-core-contract: Add an explicit design-vocab table in the stall-recovery-report.sh plan section: tokens per call site, generic-profile-only admission via vocab overrides, and clarify allowlists.tsv changes only if new chat-print fields are added (then sync code_allowlist_lines at 2344-2363 and stall-recovery-report.md allowlist block)


### FINDING_12:
- **Reviewer(s)**: Codex-dyn-core-contract
- **Severity**: important
- **Focus area**: code-quality
- **Location**: skills/implement/scripts/stall-recovery-report-allowlists.tsv:1-18; skills/implement/scripts/stall-recovery-report.sh:2344-2364; skills/implement/scripts/stall-recovery-report.md:150-172
- **Concern**: [SCOPE-REDUCTION] Token allowlist changes target the wrong parity surface. Scenario: The TSV and markdown table are field-level Tier B parity surfaces, not token-value lists. Adding design step, phase, site, or trigger tokens there adds unnecessary surface area and can break lint parity without making the tokens render-safe.
- **Proposed resolution**: Keep the TSV unchanged unless a new Tier B field is exposed. Put generic-only design tokens in safe_step_value, safe_phase_value, safe_site_value, and safe_trigger_value behind the generic profile. Keep the existing lint coverage in test-stall-recovery-report.sh.



### FINDING_1: Plan targets non-existent `design-step-clarify.sh`
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements, Codex-Generic
- **Severity**: important
- **Concern**: The plan’s `### UPDATED:` surface names `skills/design/scripts/design-step-clarify.sh`, which does not exist. Clarify handling today is orchestrator prose in `skills/design/SKILL.md` Step 0b (state fetch, plan write, publish, comment-post, label removal, `SUMMARY_OUTCOME=cancelled-clarify`). Implementing the planned script edits and `test-design-step-clarify.sh` without retargeting leaves no caller, so clarify-loop hard failures can still bypass terminal staging and the teardown gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Wire failed-clarify into design-step0-route.sh / Step 0b clarify handling or mark NEW; remove UPDATED on absent path
  - From Cursor-Requirements: Retarget clarify terminal staging to the real surface: SKILL.md Step 0b clarify branch and/or an existing wrapper such as design-step-final-summary.sh; drop or replace design-step-clarify.sh references
  - From Codex-Generic: Revise the plan to stage and run the gate in the existing Step 0b clarify branch, or explicitly create and wire the wrapper before adding its harness


### FINDING_3: Missing design success allowlist and Step 18a.5-equivalent gate contract
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The planned `design-failure-report.sh` teardown driver lacks an explicit success-outcome allowlist and sentinel-precedence contract mirroring `/implement` Step 18a.5. Without it, escalation filing may fire on cancelled/failed outcomes, or be skipped on successful escalated runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add explicit DESIGN_OUTCOME_SUCCEEDED tokens and sentinel precedence mirroring implement Step 18a.5 in design-failure-report contract


### FINDING_4: Judge-panel collapse staged as terminal failure while SKILL continues the run
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan treats judge-panel collapse (`panel-failed`, `tally-error`, `degraded-empty-collector`) as terminal failure and stages `design-failure-terminal-state.env` / `failed-panel-collapse` teardown. Current behavior: `review-design-step3-loop.sh` exits 0 on those statuses; `skills/design/SKILL.md` bypasses Gate B and continues to Step 3b, Step 4, and can finish `approved`. Mid-run terminal staging or early `render-final-summary` invocation would file a terminal bug on a later-approved teardown or violate one-issue-per-run semantics and the non-halt continuation contract. True hard stops are `postplan-failed` (e.g. `design-step3-review.sh` exits 1) and publish failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Limit Step 3 terminal staging and hard summary routing to postplan-failed only; record panel degradation as execution-issues warnings or escalation only when a script bail-out hands work to the main agent
  - From Cursor-Pragmatic: Record panel collapse as degradation/escalation ledger evidence only; reserve terminal staging for true halts (`postplan-failed`, publish failures). Run the report gate once at teardown via `render-final-summary.sh`, with terminal winning only when the run actually hard-stops


### FINDING_5:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:564-596
- **Concern**: [SCOPE-REDUCTION] Plan treats degraded panel bypass statuses as terminal halts. Scenario: Staging terminal state or failed-panel-collapse summary on panel-failed/tally-error/degraded-empty-collector either aborts runs that SKILL continues to Gate C or files terminal bugs on approved outcomes
- **Proposed resolution**: Restrict terminal staging and failed-* summary routing to hard-abort paths only; keep degraded panel as execution-issues warnings unless outcome is truly failed-shaped




### FINDING_1: postplan-failed must not emit final-summary on the Step 3 review KV stdout channel
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: If `design-step3-review.sh` invokes `render-final-summary.sh` on the `postplan-failed` path, the summary body prints on the same stdout stream as machine KVs (`STEP3_REVIEW_LOOP_STATUS`, etc.). `render-final-summary.sh --post-publish-only` always prints `final-summary.md` to stdout (lines 623–629); `read-result-env.sh` allowlists only KV keys, so orchestrator parsing breaks or misroutes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Stage `design-failure-terminal-state.env` only in `design-step3-review.sh`; export `SUMMARY_OUTCOME=failed-postplan` in `SKILL.md` and run `design-step-final-summary.sh` from the orchestrator (same pattern as `failed-plan-write`), or add a `--write-only`/no-emit flag to `render-final-summary` for embedded callers


### FINDING_2: generic-profile terminal state lacks a KV contract and implement-path overrides for classify/compose
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan stages `design-failure-terminal-state.env` but does not define required keys or how `stall-recovery-report.sh classify` runs under `--profile generic`. Today `classify` hardcodes `ship-pr-state.sh` and treats missing `STALL_TRACKING` as `no-stall` / `unrecoverable`. Without documented keys and explicit `--primary-state-file` (or equivalent) overrides on every generic helper invocation from `design-failure-report.sh`, terminal state is ignored, reports misclassify or fall through to `fallback-print` with weak root-cause evidence even when staging succeeded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Document `design-failure-terminal-state.env` keys (`STALL_STEP`, `PHASE`, `BAIL_REASON`, `EXIT_CODE`, `FAILURE_DETAIL_LOG`, etc.). Have `design-failure-report.sh` map them into `classify --profile generic --implement-tmpdir "$DESIGN_TMPDIR" --in-memory-stall-tracking true --stall-step … --phase … --failure-detail-log …`, or wire generic primary-state overrides and add harness coverage
  - From Cursor-Pragmatic: Document and implement explicit `--primary-state-file` or equivalent overrides on every generic helper invocation from `design-failure-report.sh`, mapping `design-failure-terminal-state.env` and `source-env.sh`, and add a harness case where terminal state exists without `ship-pr-state.sh`


### FINDING_3: SKILL.md SUMMARY_OUTCOME enumeration omits new failure outcomes
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The Final summary block orchestrator contract (SKILL.md ~305) lists outcomes through `failed-publish` but omits `failed-clarify`, `failed-postplan`, and `failed-publish-tail`. Step 0b clarify hard-halt prose requires exporting `SUMMARY_OUTCOME` before the Final summary block; script paths may accept new outcomes in `render-final-summary.sh`, but prompt-side clarify staging has no documented token.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add `failed-clarify`, `failed-postplan`, and `failed-publish-tail` to the `SUMMARY_OUTCOME` export list and any sibling outcome enumerations in `skills/design/SKILL.md`


### FINDING_4: Step 3 script-to-orchestrator escalations are not mechanically recorded
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Requirement 1 requires durable escalation ledgers when script-owned loops hand work to the main agent. The plan records panel degradation in scripts but leaves MAV, main-agent-apply, and `postplan-operator-required` as SKILL.md prose only (or omits `postplan-operator-required` entirely). `/implement` records ledger rows from the ship driver; a missed orchestrator line leaves expensive MAV/apply/postplan-operator recovery untracked and teardown skips escalation-success filing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add `record-escalation` calls in `skills/design/scripts/design-step3-review.sh` when `STEP3_REVIEW_LOOP_STATUS` is `main-agent-vote-required` or `main-agent-apply-required`, mirroring the planned panel-degradation hook, not only SKILL.md prose
  - From Cursor-Pragmatic: List `postplan-operator-required` in escalation triggers; record it via `stall-recovery-report.sh record-escalation` at the `design-step3-review` bail boundary; cover it in `test-design-step3-review.sh`


### FINDING_5: Tier B sensitive corpus must include design source-env.sh, not only session-env.sh
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Tier B sensitive-corpus discovery lists `session-env.sh`, but `/design` anchors session metadata on `$DESIGN_TMPDIR/source-env.sh` (written by `design-step0-session.sh`). If the corpus builder only scans `session-env.sh`, `plan.txt`, and issue-body tokens, client-bearing design text in `source-env.sh` may be omitted and Tier B validation can miss sensitive content.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Name `source-env.sh` explicitly in the corpus builder, or pass a generic-profile session-env override pointing at `$DESIGN_TMPDIR/source-env.sh` on every `compose-report` and `validate-tier-b-public-file` call


### FINDING_7: behavior-changing script updates omit required sibling .md contracts
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The plan updates `render-final-summary.sh`, `design-publish.sh`, `design-step5c.sh`, `design-step3-review.sh`, `design-step-validator-autofix.sh`, and `file-failure-report-cross-repo.sh`, and adds `test-design-step3-review.sh`, but only plans sibling docs for the new `design-failure-report` driver and one harness. That violates `.claude/rules/script-md-siblings.md`: behavior-changing scripts need updated or new sibling `.md` contracts in the same change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Add UPDATED or NEW plan sections for the affected sibling `.md` files, including `skills/design/scripts/test-design-step3-review.md` and the sibling contracts for every behavior-changing script, limited to the new reporting behavior
```

**Merge notes:** FINDING_2 subsumes Innovation + Pragmatic terminal-state/classify wiring. FINDING_4 subsumes Pragmatic MAV/apply + `postplan-operator-required` escalation gaps. Seven distinct risks remain; no empty-merge attestation applies.



### FINDING_1: Dual owners for Step 3 escalation recording (script + SKILL.md orchestrator)
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan assigns `record-escalation` to both `design-step3-review.sh` (and related script wrappers) and prompt-side SKILL.md orchestrator steps before MainAgent vote/apply/postplan-operator work. The same bail-out can be recorded twice per event (and again on resume fences), skewing ledger rows, escalation-success dedup/signatures, and filing evidence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Mirror implement SKILL.md Escalation recording owners: script wrappers (`design-step3-review.sh`, `design-step-validator-autofix.sh`) own `record-escalation`; SKILL.md only routes—explicitly forbid prompt-side `record-escalation` for statuses the wrapper already records
  - From Cursor-Pragmatic: `design-step3-review.sh` is told to call `record-escalation` on loop return while SKILL.md also tells the orchestrator to record before MainAgent vote/apply/postplan-operator work. That can append duplicate ledger rows per bail-out (and again on resume fences) Choose one owner (prefer the script fence, mirroring `run-step5-review.sh` for `coder-main-agent-required`) and delete the prompt-side `record-escalation` instructions from SKILL.md; keep orchestrator steps limited to MAV/apply/postplan work


### FINDING_2: `failed-clarify` lacks mechanical terminal-state staging before Final summary
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: Clarify hard halts set `SUMMARY_OUTCOME=failed-clarify` via prompt-only Step 0b prose, but no script/helper writes `design-failure-terminal-state.env` before the Final summary block. Teardown step 7 fail-closes when `failed-*` lacks staged terminal state, so clarify hard halts get fallback-print only and no durable filed report despite being listed as a terminal halt in scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Clarify hard halt sets SUMMARY_OUTCOME=failed-clarify but teardown step 7 fail-closes (missing terminal state) so no terminal report is filed despite the requirement Add a small staging helper (or generic stall-recovery seed path) invoked from Step 0b clarify hard-exit before design-step-final-summary.sh; cover in test-design-failure-report.sh
  - From Cursor-Pragmatic: Step 0b `failed-clarify` is prompt-only staging. Teardown step 7 fail-closes when `failed-*` lacks `design-failure-terminal-state.env`, so clarify hard halts get fallback-print only and no durable report despite being listed as terminal Add a small shared staging helper (or extend an existing Step 0b fence) that writes the terminal-state KV contract before `SUMMARY_OUTCOME=failed-clarify`; cover it in `test-design-failure-report.sh`, not only `test-design-structure.sh` prose asserts
  - From Cursor-Requirements: Add a mechanical writer (e.g. extend generic `stall-recovery-report.sh seed-terminal-state` for `design-failure-terminal-state.env`, or a small `design-stage-terminal-state.sh`) invoked from the Step 0b clarify hard-halt fence; add a hermetic harness asserting staging before `SUMMARY_OUTCOME=failed-clarify` (mirror `test-design-step3-review.sh` postplan-failed coverage)


### FINDING_3: Escalation recording must branch on `STEP3_REVIEW_LOOP_STATUS`, not remapped `LOOP_STATUS`
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: In `design-step3-review.sh`, `main-agent-apply-required`, `per-round-approval-required`, and `postplan-operator-required` rewrite `LOOP_STATUS` to `complete` before downstream handling. If `record-escalation` keys off `LOOP_STATUS`, it records the wrong trigger or skips recording entirely for those bail-outs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Plan `design-step3-review.sh` recording block: branch on `STEP3_REVIEW_LOOP_STATUS` before `LOOP_STATUS` remap; add harness asserting ledger rows for apply/postplan-operator statuses


### FINDING_5: Judge-panel collapse terminal surface missing or contradicts non-terminal Step 3 degradation paths
- **Reviewer(s)**: Cursor-Innovation, Codex-Generic
- **Severity**: important
- **Concern**: Binding scope requires terminal reporting for judge-panel collapse, but the plan classifies `panel-failed`, `tally-error`, and `degraded-empty-collector` as non-terminal (escalation evidence only on later approval). A run whose plan-review panel fully collapses can still reach Gate C and `approved` with no terminal bug filed. The plan also omits staging the existing Split-path second `panel-failed` hard exit for decompose-panel retry exhaustion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Either map judge-panel collapse to a terminal `failed-*` outcome with terminal-state staging and reporting or document an explicit scope decision that `panel-failed` is the intended judge-panel collapse surface and update the issue anchor; do not leave the contradiction implicit
  - From Codex-Generic: Add the minimal decompose-panel retry-exhaustion path: stage `design-failure-terminal-state.env`, route a `failed-judge-panel` outcome through `render-final-summary`/`design-failure-report`, and cover it in structure and failure-report tests


### FINDING_7: Escalation-success path should mirror implement Step 18a.5, not terminal `classify`
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan says "build a design classification file through the generic helper" for all paths. Escalation-success on approved runs has ledger evidence but no terminal stall state; forcing terminal `classify` conflicts with implement's `init-attempts` → root-cause → `compose-report --report-kind escalation-success` flow.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Spell out escalation-success as: ledger/fallback evidence check → `init-attempts` (zero history OK) → bounded root-cause → sensitive corpus → `compose-report --report-kind escalation-success`; reserve `classify` for terminal-failure only


### FINDING_8: Validator Cancel lacks `operator-action` sentinel and audit write before approved teardown
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: Validator autofix exhaustion records a design-failure escalation ledger before the operator prompt, but Cancel is classified as `operator-action` with no concrete sentinel or audit write planned. If the operator chooses Cancel and the run later reaches `approved`, teardown can file escalation-success instead of honoring the operator-action skip policy.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Write `design-failure-operator-action.env` and the redacted chat/run-log audit in the shared validator Cancel branch before returning or exiting; add a `design-failure-report` test for approved outcome with ledger plus operator-action sentinel skipping filing

---

**Merge notes (brief):**
- FINDING_1 + FINDING_7 → FINDING_1 (dual recording owners)
- FINDING_2 + FINDING_8 + FINDING_10 → FINDING_2 (`failed-clarify` staging)
- FINDING_5 + FINDING_11 → FINDING_5 (judge-panel collapse terminal gap)
- FINDING_3, 4, 6, 9, 12 → standalone (distinct fixes or code paths)



### FINDING_1: Decompose-panel second `panel-failed` lacks terminal failure reporting and is wired to the wrong owner
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: Step 2b.5 Split-path owns decompose-panel retry exhaustion. On a second `PANEL_STATUS=panel-failed`, `decompose-panel.md` §2/§9 and `SKILL.md` Split-path prose (line ~502) exit `/design` **1** with no `SUMMARY_OUTCOME`, no Final summary block, and no teardown failure-report gate, so durable auto-filing never runs. The plan instead stages terminal handling in `design-step3-review.sh` (~557–560), which is not on the real terminal path for decompose retry exhaustion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: After two decompose `panel-failed` outcomes Step 2b.5 exits `/design` 1 with no `SUMMARY_OUTCOME`, no Final summary block, and no teardown gate; durable filing never runs despite issue req 1 Stage terminal state via `design-stage-terminal-state.sh`, add a dedicated failed outcome (e.g. `failed-decompose-panel`), export it, and run the existing Final summary block from Split-path orchestration; update `decompose-panel.md` and SKILL.md Step 2b.5 (not Step 3)
  - From Cursor-Innovation: Move terminal staging, `failed-judge-panel` outcome, and final-summary/report-gate routing to Step 2b.5 (`decompose-panel.md`, `SKILL.md` Split-path §502, and/or a decompose helper); remove decompose retry handling from `design-step3-review.sh`
  - From Cursor-Pragmatic: Step 2b.5 Split-path second panel-failed still exits /design 1 per decompose-panel.md with no terminal-state staging or failed-judge-panel final-summary path Add decompose-panel.md and SKILL.md Split-path updates plus staging in the Step 2b.5 owner (or a small decompose helper); remove decompose retry handling from design-step3-review.sh


### FINDING_2: Terminal-state writer lacks a defined shared validation API
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The plan’s `design-stage-terminal-state.sh` depends on shared safe-value validation, but no callable helper API is defined. Without it, the script either duplicates `stall-recovery-report.sh` vocabulary validation or cannot reject unknown design tokens, violating the no-forked-helper requirement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Define the exact shared validation surface, for example a generic validate-terminal-state or validate-token path, or move that validation to the report gate and remove staging-time shared-layer claims


### FINDING_3: Operator-action chat audit may never reach the operator
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: Validator Cancel or operator-action teardown can write an audit sidecar and skip filing, but the plan does not wire a guaranteed chat-visible emission path, so the required operator-facing audit may never appear.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Choose one chat path and wire it explicitly: include the audit in final-summary notes or print a named sanitized sidecar after the summary, with render-final-summary coverage



