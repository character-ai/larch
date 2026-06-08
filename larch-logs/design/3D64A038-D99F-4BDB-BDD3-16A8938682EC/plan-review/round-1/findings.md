### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:33-34,scripts/larch-log.sh:67-84
- **Concern**: [SCOPE-REDUCTION] Implement durable flush uses both a canonical vendor-failure-diagnostics.txt batch and a scoped *.failure-diag allowlist in round_artifact_included. Scenario: Dual paths invite double-commit or allowlist drift: the same failure could land in git twice or batch-unreachable paths miss flush when allowlist rules lag call-site changes
- **Proposed resolution**: Pick one implement durable surface: either always append redacted carrier excerpts to the batch and keep per-output *.failure-diag session-only, or commit per-output *.failure-diag only and drop the separate batch slug

### FINDING_2:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/design-log-publish.sh:303-353
- **Concern**: F15 tier-specific scout raw stems lack matching deny arms in design_artifact_excluded. Scenario: After F15 writes scout-plan-manifest.json.raw.cursor / .raw.claude (and sibling sidecars), top-level staging only excludes the exact basename scout-plan-manifest.json.raw; tier intermediates pass design_artifact_excluded and get committed, violating #3534 no-raw-transcript policy
- **Proposed resolution**: Add explicit deny patterns for scout tier intermediates (e.g. scout-plan-manifest.json.raw.* and/or *.raw.cursor / *.raw.claude and their sidecars); publish only *.failure-diag carriers

### FINDING_3:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/generate-code-flow-diagram.sh:68-78; skills/implement/scripts/step-7a.sh:361-389
- **Concern**: Plan omits the direct Claude subprocess code-flow call site. Scenario: launch-claude-subprocess.sh may write code-flow-diagram.raw.md.failure-diag on timeout or JSON/CLI failure, but generate-code-flow-diagram.sh exits with only STATUS=failed and step-7a logs code-flow-diagram.stderr, so committed execution-issues and the vendor diagnostics batch can miss the actual Claude stderr/carrier
- **Proposed resolution**: Update this call path to resolve diagnostics from code-flow-diagram.raw.md and append the resolved carrier to execution-issues plus vendor-failure-diagnostics before returning failure

### FINDING_4:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lint-fix-loop.sh:360-396,428-445,552-568; scripts/ship-pr.sh:138-160,958-960
- **Concern**: Plan omits lint-fix-loop.sh as a run-external-agent/launcher consumer. Scenario: lint-fix-loop launches Codex through launch-codex-exec.sh and Cursor through run-external-agent.sh, but the proposed plan does not add saved/logged/flushed handling there; a dispatch-failed ship-pr lint-fix run can leave the new failure carrier only under lint-fix-loop scratch state while ship-pr records a generic lint-fix-loop failure file
- **Proposed resolution**: Add lint-fix-loop.sh to the audit and, on Codex/Cursor dispatch failure, resolve the per-tool carrier and append it to execution-issues and the canonical vendor-failure-diagnostics batch before emitting main-agent-required or failed

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/scout-dynamic-archetypes.sh:341-480
- **Concern**: Shared tier_raw stem lets later tier erase earlier diagnostics. Scenario: Both run_cursor_tier and run_claude_tier use tier_raw=${OUTPUT}.raw and rm -f before retry; Claude entry-clear in run-external-agent wipes Cursor attempt carrier/history tied to the same OUTPUT stem — matches incident scout-plan-manifest.json.raw.stderr overwrite
- **Proposed resolution**: Plan F15 tier stems is required; add explicit step: set tier_raw=${OUTPUT}.raw.cursor and ${OUTPUT}.raw.claude pass distinct --output to launch-review/subprocess and compose scout-level failure-diag from both stems on give-up

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/launch-review.sh:642-644
- **Concern**: Codex give-up logs live sidecar only. Scenario: Cursor path already falls back to ${OUTPUT}.diag when sidecar empty (1099-1101); codex path always passes $SIDECAR to append_launch_failure reproducing empty execution-issues blocks on health-gate fast-fail
- **Proposed resolution**: In launch-review codex give-up replace raw $SIDECAR with resolve_failure_diagnostic_source OUTPUT --sink "$SIDECAR" (and --events for codex); remove duplicate cursor-only fallback once resolver is wired

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/launch-review.sh:67-73
- **Concern**: append_launch_failure ignores REVIEW_TMPDIR and LARCH_EXECUTION_ISSUES_LOG. Scenario: Only IMPLEMENT_TMPDIR and DESIGN_TMPDIR resolve the log; /review and nested Step 5 paths with SESSION_ENV under REVIEW_TMPDIR return 0 without logging — dispatch-panel.sh relies on child launchers for vendor failures
- **Proposed resolution**: Wire append_launch_failure through the planned shared resolver (LARCH_EXECUTION_ISSUES_LOG then dirname SESSION_ENV then IMPLEMENT DESIGN REVIEW_TMPDIR) for every give-up path not only preflight F8 branches

### FINDING_8:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/generate-code-flow-diagram.sh:68-79
- **Concern**: Direct Claude subprocess code-flow launch is omitted from the site-aware logging/flush plan. Scenario: The Claude call can fail with diagnostics in code-flow-launch.err or code-flow-diagram.raw.md.failure-diag, while step-7a logs only code-flow-diagram.stderr; committed execution-issues can still miss the vendor diagnostics for this vendor-agent site
- **Proposed resolution**: Add generate-code-flow-diagram.sh/step-7a.sh to the plan: resolve the raw output carrier on generation failure, append it to execution-issues, append_vendor_failure_diagnostics, and cover it in test-generate-code-flow-diagram.sh or test-step-7a.sh

### FINDING_9:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/launch-claude-subprocess.sh:125-129
- **Concern**: Claude subprocess carrier is only written on failure and not cleared at launch start. Scenario: A failed run can leave OUTPUT.failure-diag behind; a later successful rerun using the same output path can flush stale failure diagnostics despite the retry-then-success/no-stale-carrier contract
- **Proposed resolution**: Clear OUTPUT_CANON.failure-diag after output path validation before launching Claude, and remove it on success; add a failure-then-success same-output regression test

### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/launch-review.sh:444-463
- **Concern**: F8 must wire logging on codex auth-setup even though that branch exits 0. Scenario: `external_prepare_codex_auth` writes `${OUTPUT}.diag` then `exit 0` without `append_launch_failure`; a vague “preflight” note is easy to miss because most preflights exit non-zero
- **Proposed resolution**: Explicitly list this branch in the launch-review F8 steps: `write_failure_diag` + `resolve_failure_diagnostic_source` + `append_launch_failure` before `exit 0`, and add a harness case in `scripts/test-launch-review.sh`

### FINDING_11:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/collect-agent-results.sh:1159-1160, scripts/compose-collector-failure-log.sh:70-74
- **Concern**: Retry failure carriers are not reachable from collector failure logging. Scenario: When collect-agent-results retries an empty reviewer and the retry fails, the proposed run-external-agent carrier is written on the -retry output path, but the collector keeps REVIEWER_FILE on the original output path and the planned compose-collector change only prefers REVIEWER_FILE.failure-diag; execution-issues can still miss the retry diagnostics.
- **Proposed resolution**: Teach compose-collector-failure-log or the shared collector resolver to check retry and ns-retry failure-diag candidates, or pass the retry output path in the collector record and use it when composing the failure log.

### FINDING_12:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/launch-claude-review.sh:85-88, scripts/launch-claude-review.sh:172-207, scripts/launch-claude-subprocess.sh:125-126
- **Concern**: Claude subprocess pre-output failures still have no durable carrier. Scenario: launch-claude-subprocess can fail before OUTPUT_CANON is established, so it cannot write OUTPUT.failure-diag; the wrapper captures the only diagnostic in a temporary SUBPROCESS_STDERR file that cleanup deletes, while the plan only says launch-claude-review should resolve an existing carrier.
- **Proposed resolution**: Before resolving/appending on rc != 0, have launch-claude-review compose the carrier from SUBPROCESS_STDERR with write_failure_diag --sink or persist it as OUTPUT.launcher-stderr and include that path in the resolver, batch append, and tests.

### FINDING_13:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/launch-review.sh:60-84
- **Concern**: Shared log resolver adds REVIEW_TMPDIR but local append_launch_failure still logs only when IMPLEMENT_TMPDIR or DESIGN_TMPDIR is set. Scenario: Standalone /review (and any launch-review caller with only REVIEW_TMPDIR) composes ${OUTPUT}.failure-diag via run-external-agent yet append_launch_failure returns before append-tool-failure — execution-issues stays empty so the logged acceptance criterion fails even when a carrier exists on disk
- **Proposed resolution**: Replace append_launch_failure log-path logic with the shared resolver from lib-failed-agent-stderr-tail.sh on all give-up paths (~644/1102), not only auth-setup/model-args preflight; pass resolve_failure_diagnostic_source output as --output-file; extend test-launch-review.sh with a REVIEW_TMPDIR-only fixture

### FINDING_14:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:35-36,91-92; scripts/lint-fix-loop.sh:360-433; skills/design/scripts/auto-fix-plan-commands.sh:348-397; skills/implement/scripts/generate-code-flow-diagram.sh:68-78; scripts/run-negotiation-round.sh:119-163
- **Concern**: Direct vendor-agent consumers are not routed to site-aware logging and flush paths. Scenario: The plan relies on named launchers plus a narrow larch-log allowlist, but direct cursor/codex/Claude sites can fail with only a local failure-diag and no execution-issues or vendor-failure-diagnostics batch entry, so committed logs still miss diagnostics for those launches
- **Proposed resolution**: Add these direct sites to the audit and either append their resolved carrier to execution-issues plus the canonical batch, or route them through an updated site-aware launcher that does so

### FINDING_15:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:18-20,107,124
- **Concern**: Cursor JSON result diagnostics are stripped from the committed failure carrier. Scenario: The stated requirement includes cursor JSON result/stderr as diagnostic streams, but the plan strips top-level .result from JSON sections; a Cursor failure whose only useful diagnostic is in .result would commit a carrier without the actual error text
- **Proposed resolution**: Preserve a bounded redacted failure-only excerpt of Cursor .result when exit is nonzero or is_error is true, while continuing to strip success transcripts and non-error bulk content

### FINDING_16:
- **Reviewer(s)**: Cursor-dyn-publish-flush-consistency
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/implement-finalize.sh:211-252,974-1025
- **Concern**: Step 18 teardown flushes execution-issues and commits larch-logs but the plan omits the vendor-failure-diagnostics flush helper from implement-finalize.sh. Scenario: Pre-Step-7a stalls (Step 0/2/5/12d bail) can compose carriers and append to $IMPLEMENT_TMPDIR/vendor-failure-diagnostics.txt yet never reach step-7a.sh; teardown commits larch-logs without appending that batch so acceptance flushed diagnostics are lost
- **Proposed resolution**: Mirror flush_execution_issues_safety_net: call the vendor-failure-diagnostics flush helper from implement-finalize.sh teardown before larch-log.sh commit; document in implement-finalize.md

### FINDING_17:
- **Reviewer(s)**: Codex-dyn-publish-flush-consistency
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:33,91-95; scripts/larch-log.sh:67-83,360-385; skills/review/scripts/review-core.sh:181-193; skills/review-and-fix/scripts/review-and-fix.sh:1052-1068
- **Concern**: The plan says to allowlist `*.failure-diag` only for batch-unreachable paths, but targets `round_artifact_included`, which is basename-only and cannot enforce that path/surface bound.. Scenario: `larch-log.sh write-round` passes only the basename into `round_artifact_included`, while implement review flushes call write-round from contexts that also have `IMPLEMENT_TMPDIR` and can append the canonical `vendor-failure-diagnostics` batch. A broad `*.failure-diag` allow would commit the same failure both under `round-N/` and in `vendor-failure-diagnostics.txt`; an ambiguous narrow allow risks dropping the fallback path.
- **Proposed resolution**: Revise the plan to make the batch-unreachable set exact: either keep `*.failure-diag` denied in `round_artifact_included` when all implement review producers append the batch, or change the write-round predicate to receive the relative path/source context and allow only named batch-unreachable patterns. Add the planned `test-larch-log.sh` case for both a batch-reachable non-stage and any explicit batch-unreachable allowed path.

### FINDING_18:
- **Reviewer(s)**: Cursor-dyn-ordering-invariant
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/launch-codex-implement.sh:315-363 scripts/launch-cursor-implement.sh:240-276 scripts/launch-codex-ci.sh:167-206 scripts/launch-cursor-ci.sh:105-188
- **Concern**: Implement/CI launcher sections prescribe give-up ordering B only while auth-setup model-args and binary-missing paths exit before run-external-agent. Scenario: Those preflights never get a trap-produced failure-diag; give-up B resolve-only would log empty execution-issues (incident shape)
- **Proposed resolution**: Add explicit give-up-A steps per path: write_failure_diag with branch sink/.diag resolve append_launch_failure and batch; mirror launch-review.sh F8 and launch-codex-exec.sh:58-59

### FINDING_19:
- **Reviewer(s)**: Codex-dyn-ordering-invariant
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/launch-codex-implement.sh:314-330,348-363; scripts/launch-cursor-implement.sh:236-276; scripts/launch-codex-ci.sh:161-182,198-206; scripts/launch-cursor-ci.sh:104-106,180-188; scripts/launch-claude-ci.sh:170-198
- **Concern**: Plan gives these launcher sections resolve/post-wrapper handling, but they have no-wrapper preflight or direct-launch paths that never get a run-external-agent failure carrier. Scenario: Auth setup, model-args, binary-missing, or direct Claude failures can exit before the wrapper-created carrier exists, so resolve plus append can still leave no composed carrier or durable batch entry for those failures
- **Proposed resolution**: Revise each listed site to use give-up-ordering A on no-wrapper/direct failure branches: write_failure_diag from the branch sink/stderr/diag, resolve it, then append_launch_failure and append_vendor_failure_diagnostics before the existing exit or KV return; keep ordering B only for post-run-external-agent give-up

### OOS_1:
- **Description**: [SCOPE-REDUCTION] Triple durable flush surfaces per failure. Scenario: ${OUTPUT}.failure-diag plus vendor-failure-diagnostics.txt batch plus larch-log.sh scoped allowlist increases double-commit and drift risk beyond SIMPLE minimum; issue only requires committed distinguishable diagnostics
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: plan.txt approach 6-8
- **Phase**: design

### OOS_2:
- **Description**: [OUT_OF_SCOPE] dispatch-panel.sh ship-pr.sh lint-fix-loop.sh not listed. Scenario: Issue asks audit all vendor sites; dispatch-panel orchestrates scout-dynamic-archetypes; ship-pr and lint-fix-loop already source lib-failed-agent-stderr-tail and append-tool-failure with separate stderr-tail semantics
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: plan.txt Files to modify
- **Phase**: design
