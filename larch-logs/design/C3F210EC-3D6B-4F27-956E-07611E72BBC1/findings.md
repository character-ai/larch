### FINDING_1:
- **Reviewer(s)**: unknown-slot, unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/breadcrumb-monitor.sh (planned)
- **Concern**: Monitor completion depends on a harness task id that repo shell code cannot observe. Scenario: The helper may hang or exit without the background script status because Bash task notifications are harness-level events, not filesystem sentinels available to a script
- **Proposed resolution**: Replace --task-id as the completion authority with explicit --done-sentinel and --status-file paths set by the launch block and written by the child process trap

### FINDING_2:
- **Reviewer(s)**: unknown-slot, Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lib-quiet.sh:37-75
- **Concern**: Foreground-duplication guard relies on child env mutation affecting the parent monitor call. Scenario: If LARCH_QUIET_BREADCRUMBS_ALREADY_SURFACED is exported before the launch, the paired monitor can inherit it and silently suppress normal background streams; if the child unsets it, that does not change the parent shell environment
- **Proposed resolution**: Scope the guard to the child command only or use a child-written marker file that the monitor reads; document the exact launch snippet

### FINDING_3:
- **Reviewer(s)**: unknown-slot, Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ci-wait.sh:67-170, scripts/collect-agent-results.sh:184-307, skills/implement/scripts/step2-implement.sh:70-402
- **Concern**: Installing larch_quiet_install_done_sentinel immediately after larch_quiet_init will be overwritten by later EXIT traps. Scenario: ci-wait.sh, collect-agent-results.sh, and step2-implement.sh install EXIT traps after quiet init, so the proposed sentinel trap would disappear and breadcrumb-monitor.sh would wait forever
- **Proposed resolution**: Install the done-sentinel hook after each script's final EXIT trap or introduce a shared on-exit registry/wrapper that composes future cleanup and sentinel behavior

### FINDING_4:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/lib-quiet.sh:114-125
- **Concern**: Structured breadcrumb categories have no API surface. Scenario: emit_breadcrumb currently accepts only text, while the plan requires c=progress|warn|stall|retry|... and says no per-callsite rewording is required; category quality would depend on fragile text inference
- **Proposed resolution**: Add an explicit category argument or option, migrate audited call sites, and make tests assert category fields for warn/stall/retry examples

### FINDING_5:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/research/references/research-phase.md:188-195, skills/research/references/validation-phase.md:182-189, skills/shared/external-reviewers.md:44-51
- **Concern**: Rewrite surface omits Markdown files still carrying the old foreground contract. Scenario: After the lint flips hard-fail, these tracked skill/reference files would still contain old Foreground required banners and denylisted collect-agent-results.sh examples
- **Proposed resolution**: Expand the file list to every path returned by the foreground-marker linter/rg scan, including research references and skills/shared/external-reviewers.md

### FINDING_6:
- **Reviewer(s)**: unknown-slot, unknown-slot
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: Makefile:824-825, Makefile:910-913
- **Concern**: New test-breadcrumb-monitor harness is not wired into Makefile targets. Scenario: The plan's CI command make test-breadcrumb-monitor would fail because the plan creates scripts/test-breadcrumb-monitor.sh but does not update Makefile or harness shard wiring
- **Proposed resolution**: Add Makefile target, harness aggregate shard entry, docs/linting.md target row, and any agent-lint exclusions matching existing Makefile-only harness patterns

### FINDING_7:
- **Reviewer(s)**: unknown-slot
- **Severity**: latent
- **Focus area**: security
- **Location**: scripts/redact-secrets.sh:23-28, scripts/breadcrumb-monitor.sh (planned)
- **Concern**: Streaming arbitrary --stream/--quiet-log paths to chat relies on a partial redactor. Scenario: The redactor explicitly does not cover opaque bearer tokens, DB strings, private hostnames, PII, or several provider tokens; a bad or symlinked stream path could expose unrelated local content
- **Proposed resolution**: Constrain stream and quiet-log paths to the session tmpdir/breadcrumb directory, reject symlinks and non-regular files, create files with private modes, and document redaction as defense-in-depth rather than authorization

### FINDING_8:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/run-step5-review.sh:6-10; skills/implement/scripts/run-step2-dispatch.sh:71-88; scripts/ci-wait.sh:160-170; scripts/collect-agent-results.sh:303-308; skills/implement/scripts/step2-implement.sh:401-402
- **Concern**: Done-sentinel rollout is specified as a one-line call after larch_quiet_init, but two denylisted wrappers have no lib-quiet init and later EXIT traps in other denylisted scripts would overwrite a trap installed that early. Scenario: Backgrounded run-step5-review.sh or run-step2-dispatch.sh never touches LARCH_DONE_SENTINEL, and ci-wait/collector/step2 replace the sentinel trap, so breadcrumb-monitor can wait forever or miss failure completion
- **Proposed resolution**: Either move completion into breadcrumb-monitor using the actual Bash task notification, or add a trap-append helper and update each existing trap site; add lib-quiet init/sentinel support to the wrapper scripts only if their stdout contracts remain intact

### FINDING_9:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/breadcrumb-monitor.md (NEW); scripts/lib-quiet.sh:70-75
- **Concern**: Foreground-duplication guard relies on LARCH_QUIET_BREADCRUMBS_ALREADY_SURFACED being set by the parent and unset by the child. Scenario: Environment mutation is process-local; the monitor sibling never sees the child unset, so if the parent exports the guard it exits silently for normal background launches, otherwise it cannot learn foreground FD3 status
- **Proposed resolution**: Use an explicit file/status record written by the child before first breadcrumb, or have the caller choose monitor mode from actual tool execution; do not model cross-process state with env unsets

### FINDING_10:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/lint-foreground-markers.sh:337-354; BASH_AUTHORING.md:50-68
- **Concern**: Proposed lint treats run_in_background true and breadcrumb-monitor --task-id as shell-fence tokens even though run_in_background and the task id are Bash-tool metadata outside the shell body. Scenario: A fence can pass lint by containing inert comments or invalid shell, while real tool calls may still be foreground or lack a captured task id; conversely a correct two-tool sequence may fail because the metadata is not in the fenced command
- **Proposed resolution**: Define copyable marker comments that explicitly document tool metadata, or move the pair into a real helper/driver script that launches and monitors itself; update lint to validate that representation

### FINDING_11:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/design-log-publish.sh:257-274; scripts/larch-log.sh:67-101; scripts/larch-log-batches.sh:6-34; docs/run-logs.md:11-62
- **Concern**: Plan documents committed breadcrumb streams under larch-logs but does not add any staging or batch path that would copy the proposed breadcrumbs/<script>.<launch-id>.ndjson files. Scenario: Chat propagation may work during the run, but post-hoc larch-logs omit breadcrumb streams despite docs claiming they are committed, and completeness/redaction tests have no source of truth
- **Proposed resolution**: Either drop the committed-log claim or add an explicit breadcrumb batch/round artifact allowlist and design-log-publish recursion for the breadcrumbs directory, with sanitizer and tests

### FINDING_12:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: code-quality
- **Location**: Makefile:4-16; agent-lint.toml:645-648; docs/linting.md:17
- **Concern**: The plan adds scripts/test-breadcrumb-monitor.sh and says to run make test-breadcrumb-monitor, but Makefile and agent-lint reachability updates are not in the file list. Scenario: make test-breadcrumb-monitor is undefined and the new Makefile-only harness can be flagged by agent-lint as dead/orphaned, so the proposed CI command either cannot run or is not protected by the existing harness infrastructure
- **Proposed resolution**: Add Makefile .PHONY, target recipe, test-harness shard membership, docs/linting row, and agent-lint excludes for the new harness and sibling contract

### FINDING_13:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lib-quiet.sh:70-75
- **Concern**: FINDING_1: Foreground-duplication guard relies on a background child unsetting an env var that the foreground monitor already inherited. Scenario: The plan says the parent sets LARCH_QUIET_BREADCRUMBS_ALREADY_SURFACED=1 before launch and lib-quiet.sh unsets it inside the child when FD 3 is surfaced, but child env mutations cannot propagate back to the parent or sibling breadcrumb-monitor.sh process; the monitor can exit silently on every normal background run and lose all breadcrumbs
- **Proposed resolution**: Replace the env-var handoff with an explicit sidecar/sentinel written by the child and read by the monitor, or invert the default so the monitor streams unless a child-written already-surfaced marker exists; add a test where the child unsets the variable and prove the monitor still streams

### FINDING_14:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/dispatch-with-waterfall.sh:242; skills/implement/scripts/run-step2-dispatch.sh:88-104; scripts/run-step5-review.sh:179-240
- **Concern**: FINDING_2: One inherited LARCH_DONE_SENTINEL can be touched by nested denylisted helpers before the top-level background task is done. Scenario: The plan adds larch_quiet_install_done_sentinel to all nine scripts, but several denylisted scripts synchronously call another denylisted script; collect-agent-results.sh can touch the same sentinel while dispatch-with-waterfall.sh still has later waterfall work, step2-implement.sh can touch it before run-step2-dispatch.sh returns, and review-and-fix.sh can touch it before run-step5-review.sh finishes
- **Proposed resolution**: Make sentinel ownership top-level only, for example by recording an owner PID/task token and touching only when $$ matches it, or by unexporting/replacing LARCH_DONE_SENTINEL for nested helper calls; add regression coverage for each nested denylisted invocation

### FINDING_15:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: security
- **Location**: scripts/redact-secrets.sh:74-95
- **Concern**: FINDING_3: Per-line redaction breaks the existing multi-line PEM fail-closed contract. Scenario: redact-secrets.sh tracks PEM blocks across a stream; if breadcrumb-monitor.sh invokes it independently for each breadcrumb or quiet-log line, the BEGIN line is replaced but following key body lines are processed without in_pem state and can print raw, especially in the planned failure tail path
- **Proposed resolution**: Redact the whole quiet log before tailing and keep a persistent redaction stream for monitored output, or extend the redactor with a safe line-local mode that cannot leak PEM bodies; add tests for full PEM blocks and tails that start mid-key

### FINDING_16:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: security
- **Location**: scripts/larch-log.sh:251-257; scripts/larch-log.sh:487-500; scripts/larch-log.md:54-64
- **Concern**: FINDING_4: Committing breadcrumb stream files is planned without a redacted larch-log write path. Scenario: larch-log.sh redacts write/append payloads, but commit copies and stages the whole run directory as-is; if breadcrumb streams are placed under larch-logs to satisfy docs/run-logs.md, raw stream content can bypass larch_log_redact_file and be committed
- **Proposed resolution**: Define a registered breadcrumb batch or explicit redacted-copy step through larch-log.sh before files enter the committed run directory; do not rely on larch-log commit to sanitize arbitrary files

### FINDING_17:
- **Reviewer(s)**: Codex-Edge, unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ci-wait.sh:67,170; scripts/collect-agent-results.sh:184,307; skills/implement/scripts/step2-implement.sh:70,402
- **Concern**: DONE sentinel trap can be overwritten by later EXIT traps. Scenario: The plan adds larch_quiet_install_done_sentinel immediately after larch_quiet_init, but several target scripts install EXIT traps later; those later trap calls replace the sentinel trap, so breadcrumb-monitor.sh may never observe completion
- **Proposed resolution**: Install the sentinel after each script's final EXIT trap or provide a trap-chaining helper and update later trap sites to use it; add tests where a later trap is installed after the sentinel helper

### FINDING_18:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/run-step5-review.sh:1-10; scripts/run-step5-review.sh:239-240; skills/implement/scripts/run-step2-dispatch.sh:1-4; skills/implement/scripts/run-step2-dispatch.sh:104
- **Concern**: Two denylisted wrappers have no larch_quiet_init call for the planned sentinel insertion. Scenario: The plan says all nine scripts gain larch_quiet_install_done_sentinel immediately after larch_quiet_init, but run-step5-review.sh and run-step2-dispatch.sh do not source lib-quiet.sh or call larch_quiet_init; wrapper-level early failures will not produce the planned sentinel or quiet-log contract
- **Proposed resolution**: Add lib-quiet.sh sourcing and larch_quiet_init to those wrappers, or remove them from the sentinel-owned denylist and monitor the child scripts instead; define which process owns the done sentinel and quiet log

### FINDING_19:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: security
- **Location**: docs/run-logs.md:64; scripts/larch-log.sh:67-123
- **Concern**: Breadcrumb streams are documented as committed with redaction but no log pipeline is planned. Scenario: The new stream file is written from emit_breadcrumb before monitor-time redaction, while docs/run-logs.md promises larch-logs redaction and larch-log.sh only copies registered batches and round artifacts; this can either drop the promised artifacts or commit raw breadcrumb text if copied ad hoc
- **Proposed resolution**: Add an explicit larch-log batch or round artifact path for breadcrumb streams, run it through lib-redact before commit, register it in larch-log-batches, and test secrets/tmpdir redaction on committed breadcrumb files

### FINDING_20:
- **Reviewer(s)**: Codex-Edge
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/lib-quiet.sh:114-124
- **Concern**: PIPE_BUF atomicity is applied to regular-file appends. Scenario: The plan relies on a single printf under PIPE_BUF to prevent interleaving, but LARCH_BREADCRUMB_STREAM is a regular file, not a pipe; concurrent nested helpers can still produce torn or interleaved structured records depending on shell write behavior
- **Proposed resolution**: Use a portable lock around appends, or write per-PID streams and merge them; make the nesting test spawn concurrent processes and validate every record parses

### FINDING_21:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: Makefile:4; Makefile:65-71; Makefile:824-825; agent-lint.toml:124-127
- **Concern**: The new breadcrumb monitor test is not wired into the build plan. Scenario: The testing strategy requires make test-breadcrumb-monitor, but the file list does not include Makefile or agent-lint updates; CI/local verification can fail with no such target or leave the new harness unrun
- **Proposed resolution**: Add test-breadcrumb-monitor to .PHONY, a Makefile target, a test-harness shard, and agent-lint exclusions if the harness is Makefile-only

### FINDING_22:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: code-quality
- **Location**: scripts/lint-foreground-markers.sh:237-305
- **Concern**: Linter rewrite spec is internally inconsistent about requiring both halves of the pair. Scenario: The approach says run_in_background and breadcrumb-monitor are both required, but the file-specific rewrite says the structural check requires either run_in_background or a monitor line; implementing the latter lets a denylisted launch pass without its foreground consumer
- **Proposed resolution**: Specify and implement per-anchor AND semantics: the launch fence must contain run_in_background true and the same or adjacent allowed window must contain a matching breadcrumb-monitor invocation; add negative tests for each missing half

### FINDING_23:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ci-wait.sh:67-170; scripts/collect-agent-results.sh:184-307; skills/implement/scripts/step2-implement.sh:70-402
- **Concern**: The plan installs larch_quiet_install_done_sentinel immediately after larch_quiet_init, but these scripts install EXIT traps later. Scenario: Those later trap calls overwrite the done-sentinel trap, so breadcrumb-monitor.sh can wait forever or miss completion on ci-wait, collect-agent-results, or step2-implement
- **Proposed resolution**: Install the done sentinel after each script's final EXIT trap, or implement a real trap-composition helper and update every later trap site to use it

### FINDING_24:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:1018-1029; skills/implement/SKILL.md:1215-1227; skills/implement/SKILL.md:1568-1578
- **Concern**: The proposed paired-launch pattern exports only LARCH_BREADCRUMB_STREAM, while the completion mechanism depends on LARCH_DONE_SENTINEL or an unavailable shell-visible task-notification contract. Scenario: The foreground monitor has no reliable completion file to watch, so it can continue tailing after the background script exits or rely on a harness task id that Bash cannot resolve
- **Proposed resolution**: Make every rewritten callsite allocate and export LARCH_DONE_SENTINEL next to LARCH_BREADCRUMB_STREAM, pass it to breadcrumb-monitor.sh, and test a launch+monitor block end to end

### FINDING_25:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: security
- **Location**: scripts/lib-quiet.sh:114-122; docs/run-logs.md:1-5
- **Concern**: The plan writes raw breadcrumb streams from emit_breadcrumb but also says those streams are committed under larch-logs with redaction guarantees. Scenario: Secrets present in breadcrumb text would be redacted for chat display but preserved in committed breadcrumb files
- **Proposed resolution**: Add source-side redaction before appending to LARCH_BREADCRUMB_STREAM, or keep raw streams tmpdir-only and commit only a redacted copy produced by the same scrubber

### FINDING_26:
- **Reviewer(s)**: unknown-slot
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/ci-wait.sh:180-273
- **Concern**: The plan audits emit_breadcrumb callsites, but ci-wait progress is emitted through larch_errf dots/status lines, not emit_breadcrumb. Scenario: After switching ci-wait.sh to background+monitor, long CI waits can still appear silent because no breadcrumb records are appended during the poll loop
- **Proposed resolution**: Convert ci-wait progress/status larch_errf calls to emit_breadcrumb-compatible records, or teach lib-quiet to mirror selected larch_err output to the breadcrumb stream

### FINDING_27:
- **Reviewer(s)**: unknown-slot
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: Makefile:4; Makefile:65; Makefile:326-330; Makefile:824-825; agent-lint.toml:645-648
- **Concern**: The plan creates scripts/test-breadcrumb-monitor.sh and expects make test-breadcrumb-monitor, but does not update Makefile shards or agent-lint reachability exclusions. Scenario: The new harness is not run by make lint/test-harnesses and may be flagged as unreachable by agent-lint
- **Proposed resolution**: Add test-breadcrumb-monitor to .PHONY, a Makefile target, one test-harnesses shard, docs/linting.md, and agent-lint exclusions beside test-lib-quiet/test-lint-foreground-markers

### FINDING_28:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lib-quiet.sh:114-124; scripts/ship-pr.sh:584-598
- **Concern**: Finding 1: Structured breadcrumb records have no reliable category or escaping contract. Scenario: `emit_breadcrumb` currently accepts only free-form text, while the plan expects `c=<enum>` and machine-parseable `text=<...>`; existing callsites use symbolic prefixes and free-form text, so categories and text boundaries will be guessed rather than guaranteed.
- **Proposed resolution**: Use compact JSONL for the stream or add an explicit category argument plus escaping/back-compat shim, then migrate and test denylisted plus nested `emit_breadcrumb` callsites.

### FINDING_29:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/run-step5-review.sh:1-9; scripts/run-step5-review.sh:239-240; skills/implement/scripts/run-step2-dispatch.sh:1-9; skills/implement/scripts/run-step2-dispatch.sh:104
- **Concern**: Finding 3: Two denylisted wrapper scripts have no quiet init site for the proposed sentinel call. Scenario: `run-step5-review.sh` and `run-step2-dispatch.sh` are on the rollout list, but they do not source `lib-quiet.sh` or call `larch_quiet_init`; the plan's "add after larch_quiet_init" instruction is not actionable for them.
- **Proposed resolution**: Decide explicitly whether these wrappers should gain quiet init/sentinel support or whether completion should be owned only by their child scripts, then update the lint/docs/tests to match that ownership.

### FINDING_30:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-implement-anti-polling-rule.sh:53-76
- **Concern**: Finding 4: The plan rewrites Step 5 to background+monitor but does not update the harness that forbids Step 5 `run_in_background: true`. Scenario: `make lint` runs this harness, and it currently fails on any Step 5 `run_in_background: true` outside foreground banners.
- **Proposed resolution**: The PR will fail its required checks after the SKILL rewrite. Replace this assertion with the new invariant: every Step 5 Family B launch must have a background marker, stream path, and paired `breadcrumb-monitor.sh` consumer.

### FINDING_31:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/review/references/heavy-worker.md:53-56; skills/design/references/dialectic-execution.md:108-116
- **Concern**: Finding 5: The proposed `--task-id <bg-id>` pairing assumes a task id can be passed into a shell helper in the same orchestration step. Scenario: Current wait contracts avoid harness task IDs by waiting on deterministic output and `.done` files; a Bash script cannot observe Claude's background task notification, and a same-message paired call cannot know the prior tool call's returned task id before it runs.
- **Proposed resolution**: Use a repo-local done/exit-code sentinel path created before launch, or introduce a single foreground wrapper that starts the child, tails the breadcrumb stream, waits, and returns the child exit code. This avoids depending on harness-private task IDs.

### FINDING_32:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: latent
- **Focus area**: security
- **Location**: scripts/larch-log.sh:251; scripts/lib-larch-log.sh:88-95; docs/run-logs.md:64
- **Concern**: Finding 6: The plan says breadcrumb streams are committed with run logs but does not add a redacted larch-log batch or copy path. Scenario: Committed run-log payloads currently pass through `larch_log_redact_file`; breadcrumb streams are proposed under session tmpdirs, and only `docs/run-logs.md` is listed for the committed-log contract.
- **Proposed resolution**: An ad hoc later copy could bypass the established redaction pipeline, or the docs will promise an artifact that is never committed. Add a registered batch/round artifact path that uses `larch-log.sh` redaction, with verifier and batch-table tests, or drop the committed-stream claim.

### FINDING_33:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ci-wait.sh:127-170
- **Concern**: The proposed done sentinel is touch-only and loses the child exit code. Scenario: Failure UX requires STATUS=<exit_code> and failure-tail output, but larch_quiet_install_done_sentinel is described as touching LARCH_DONE_SENTINEL; breadcrumb-monitor.sh cannot distinguish success from failure
- **Proposed resolution**: Have larch_quiet_install_done_sentinel capture $? and atomically write the numeric exit code to the sentinel, matching the existing ci-wait.sh output-file done-file contract

### FINDING_34:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ci-wait.sh:67-170
- **Concern**: Installing the done-sentinel trap immediately after larch_quiet_init will be clobbered by scripts that install later EXIT traps. Scenario: ci-wait.sh installs its own EXIT trap after validation; step2-implement.sh and collect-agent-results.sh also install cleanup traps later, so the proposed one-line call near the top will not reliably write the completion sentinel
- **Proposed resolution**: Require each denylisted script to integrate the sentinel write into its final EXIT trap after script-specific traps are known, or provide an explicit trap-stack API and update later trap callsites to use it

### FINDING_35:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lib-quiet.sh:70-75
- **Concern**: The foreground-duplication guard relies on child environment mutation reaching the sibling monitor. Scenario: The plan says the parent sets LARCH_QUIET_BREADCRUMBS_ALREADY_SURFACED before launch and lib-quiet.sh unsets it inside the child when FD-3 is surfaced, but that unset cannot modify the already-started monitor process environment; the monitor will suppress all output or fail to suppress duplicates depending on launch ordering
- **Proposed resolution**: Use a filesystem sentinel or stream header written by the child to communicate actual surfacing state, or remove the fallback path and only use the monitor for required-background launches

### FINDING_36:
- **Reviewer(s)**: unknown-slot
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/larch-log-batches.sh:6-34
- **Concern**: The plan documents committed breadcrumb streams without adding a larch-log batch or copy path. Scenario: docs/run-logs.md would promise breadcrumb files under larch-logs, but the batch registry and refresh/commit flow only persist registered batches and write-round artifacts, so breadcrumb streams created under session tmpdirs are lost at cleanup
- **Proposed resolution**: Add an explicit breadcrumb-stream batch or a write-round allow-list entry plus refresh-run-logs integration, or drop the committed-log claim from the plan

### FINDING_37:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lib-quiet.sh:70-75; scripts/breadcrumb-monitor.md:1
- **Concern**: Foreground duplication guard relies on parent env state that a child cannot mutate for the monitor. Scenario: Parent sets LARCH_QUIET_BREADCRUMBS_ALREADY_SURFACED=1, the foreground monitor inherits it and exits silently, while the child unsetting it cannot propagate back to that monitor process
- **Proposed resolution**: Use a shared sentinel/status file written by the child when foreground surfacing is actually detected, or drop the guard for required background launches; do not base monitor suppression on child-side env mutation

### FINDING_38:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lib-quiet.sh:114-125; scripts/breadcrumb-monitor.sh:1
- **Concern**: Done sentinel is specified as touch-only, so the monitor cannot reliably emit STATUS or failure tails. Scenario: When a background ship/review/collector script fails, breadcrumb-monitor may only observe completion and cannot know the exit code unless an external task-id wait primitive exists, so STATUS and failure-tail behavior become unreliable
- **Proposed resolution**: Make larch_quiet_install_done_sentinel write an atomic status file containing EXIT_CODE=<rc> from the EXIT trap, and have breadcrumb-monitor wait on that status contract instead of an unresolved harness task-id wait assumption

### FINDING_39:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: Makefile:4-79; Makefile:824-825; agent-lint.toml:742-745
- **Concern**: New breadcrumb monitor harness is not wired into the repo validation surface. Scenario: The plan requires make test-breadcrumb-monitor, but without Makefile PHONY/target/shard registration and agent-lint exemptions the target will be missing or the harness will not run under make lint/CI
- **Proposed resolution**: Add test-breadcrumb-monitor to .PHONY, a Makefile target, one test-harnesses-N shard, docs/linting.md, and the relevant agent-lint.toml script/sibling-doc allow-list entries

### FINDING_40:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/larch-log.md:94-97; scripts/larch-log-batches.md:3-19; docs/run-logs.md:11-64
- **Concern**: Run-log persistence promise for breadcrumb streams has no corresponding larch-log batch or publisher change. Scenario: The plan says breadcrumb stream files are committed with the same redaction guarantees, but only docs/run-logs.md is listed; without larch-log registry/publish/test changes the files are either not committed or get copied ad hoc outside the sanitizer contract
- **Proposed resolution**: Either remove the committed-stream promise from docs/run-logs.md, or add a registered batch/copy path in larch-log, sanitizer coverage, and tests proving breadcrumb streams are redacted before commit

### FINDING_41:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:11-12; plan.txt:32-37
- **Concern**: Completion/status handshake is under-specified. Scenario: Callsites only export LARCH_BREADCRUMB_STREAM and monitor takes --task-id/--stream, so the helper has no concrete done sentinel, exit-code source, or required quiet-log path to know when to stop and produce STATUS/failure tail.
- **Proposed resolution**: Define the launch template to allocate/export LARCH_DONE_SENTINEL and LARCH_QUIET_LOG_FILE, pass --done-sentinel/--status-file/--quiet-log to breadcrumb-monitor.sh, and document how the Bash tool task id is captured.

### FINDING_42:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:16; plan.txt:71-81
- **Concern**: Lint contract weakens required pairing. Scenario: The implementation section says run_in_background or breadcrumb-monitor is enough, conflicting with the stated both-required acceptance and leaving consumer-present foreground launches or background launches without monitors potentially passing.
- **Proposed resolution**: Change the lint spec to require both tokens for each denylisted anchor, require old foreground marker failure, and add negative tests for consumer-without-background and background-without-consumer.

### FINDING_43:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:14; plan.txt:61; plan.txt:127-129; scripts/lib-quiet.sh:101-112
- **Concern**: Model-actionable category emission is not specified. Scenario: The record requires c=<category>, but emit_breadcrumb currently accepts only free text and the plan says existing breadcrumb strings are fine, so implementers have no way to assign warn/stall/retry/etc consistently.
- **Proposed resolution**: Extend emit_breadcrumb with an explicit category option/argument or documented inference table, update representative callsites, and add tests asserting every stream record has a valid c= value.

### FINDING_44:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: security
- **Location**: plan.txt:11; plan.txt:123-125; scripts/larch-log-batches.sh:6-34
- **Concern**: Raw breadcrumb streams are planned as committed logs without a redaction path. Scenario: The writer appends raw emit_breadcrumb text to LARCH_BREADCRUMB_STREAM and only monitor stdout is redacted, while the run-log docs update says breadcrumb files are committed under larch-logs and no larch-log batch/sanitizer is added.
- **Proposed resolution**: Add a breadcrumb larch-log batch or flush step that redacts secrets/tmpdir/internal data before commit, and test raw secret breadcrumbs never reach committed artifacts.

### FINDING_45:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: code-quality
- **Location**: plan.txt:44-57; plan.txt:150-154; Makefile:4; Makefile:824-825
- **Concern**: Test target for new monitor harness is missing from planned file changes. Scenario: Testing strategy requires make test-breadcrumb-monitor, but the plan creates the script only and does not update Makefile phony list, target body, or harness shard, so CI/local make lint cannot run it.
- **Proposed resolution**: Add Makefile updates and a docs/linting target entry; include the new target in a test-harnesses shard and .PHONY.

### FINDING_46:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:11-12, plan.txt:61, plan.txt:133
- **Concern**: Callsite contract does not set the done sentinel or deterministic quiet-log path that the monitor depends on. Scenario: Backgrounded scripts may finish but breadcrumb-monitor cannot reliably detect completion, recover exit status, or print the required failure tail
- **Proposed resolution**: Add explicit per-launch LARCH_DONE_SENTINEL and LARCH_QUIET_LOG_FILE setup, pass them to breadcrumb-monitor.sh, and test the generated skill examples

### FINDING_47:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/run-step5-review.sh:1-10; skills/implement/scripts/run-step2-dispatch.sh:1-13
- **Concern**: Two denylisted scripts have no lib-quiet initialization, but the plan says every denylisted script gets larch_quiet_install_done_sentinel after larch_quiet_init. Scenario: The proposed one-line edit is impossible for these wrappers, so their top-level completion sentinel path can be missed
- **Proposed resolution**: Revise the plan to add lib-quiet sourcing and larch_quiet_init to those wrappers with stdout/stderr regression tests, or document a different sentinel owner for them

### FINDING_48:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:14, plan.txt:127-129; scripts/lib-quiet.sh:114-123
- **Concern**: Structured breadcrumb category generation is underspecified while existing emit_breadcrumb calls pass only free-form prose. Scenario: The new model-actionable c= field can become arbitrary, missing, or guessed inconsistently, failing the acceptance criterion for category vocabulary
- **Proposed resolution**: Add an explicit emit_breadcrumb category API or deterministic classifier, update/audit callsites where needed, and add tests for every allowed category plus unknown input

### FINDING_49:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: code-quality
- **Location**: plan.txt:44-53, plan.txt:154; Makefile:1-15, Makefile:824-825
- **Concern**: The plan adds make test-breadcrumb-monitor but does not include Makefile or harness-shard wiring. Scenario: The named CI/local validation command will not exist or will not run under make lint/test-harnesses
- **Proposed resolution**: Add Makefile .PHONY and target entries, place test-breadcrumb-monitor in exactly one test-harnesses shard, and run the shard coverage guard

### FINDING_50:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:123-125; scripts/larch-log-batches.sh:6-34; scripts/larch-log.sh:89-123
- **Concern**: Plan documents committed breadcrumb stream files under larch-logs but does not add a larch-log batch or round artifact path to actually copy and redact them. Scenario: Docs can claim breadcrumb streams are durable while no committed artifact is produced, or raw files are copied by an ad hoc path outside the batch contract
- **Proposed resolution**: Register a breadcrumb batch or round artifact pattern, route it through larch-log redaction/validation, and update run-log completeness tests

### FINDING_51:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: security
- **Location**: plan.txt:36-37, plan.txt:123-125, plan.txt:137; SECURITY.md:104, SECURITY.md:124
- **Concern**: Plan changes redaction and committed log behavior but omits SECURITY.md. Scenario: Secret-handling expectations for raw breadcrumb streams, chat redaction, failure tails, and larch-logs allowlisting remain undocumented
- **Proposed resolution**: Add SECURITY.md updates covering raw session breadcrumb streams, fail-closed monitor redaction, committed-log redaction, and residual sensitive-content risks

### FINDING_52:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: architecture
- **Location**: <TMPDIR>/plan.txt:12,34-35,40-42,144; AGENTS.md:56; BASH_AUTHORING.md:52-68
- **Concern**: Plan treats shell-triggered Monitor as primary without a confirmed repo contract. Scenario: Repository docs only describe Monitor as an assistant/harness primitive and grep found no monitor:start, task-id, or wait-id shell API; breadcrumb-monitor.sh may always fall back while docs/tests still claim Monitor-bound near-real-time delivery
- **Proposed resolution**: Make the wc-offset reader the specified primary path unless a real shell-invocable Monitor contract is proven; document exact observable activation in scripts/breadcrumb-monitor.md and add tests that force primary/fallback selection

### FINDING_53:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:35,47,51,144
- **Concern**: Fallback timing and offset semantics are underspecified and internally inconsistent. Scenario: The test claim says DONE sentinel exits within 1 second, but failure-mode text says fallback default polling latency is 2 seconds; the plan also says byte offsets via wc -c but lists tail -n +N and does not define final-drain ordering when the writer appends just before touching DONE
- **Proposed resolution**: Specify a Bash 3.2 loop precisely: parse wc -c safely, read bytes from old_offset+1 through new_offset, update bookmark only after successful redacted print, perform a final drain after observing DONE, handle missing/truncated files, and either use sub-second polling or relax the 1-second assertion

### FINDING_54:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:61,127-129; scripts/ci-wait.sh:67,170; scripts/collect-agent-results.sh:184,300-307; skills/implement/scripts/step2-implement.sh:70,401-402
- **Concern**: DONE sentinel trap composition is planned too early for scripts that install later EXIT traps. Scenario: Inserting larch_quiet_install_done_sentinel immediately after larch_quiet_init will be overwritten by later trap EXIT assignments in existing denylisted scripts, so breadcrumb-monitor.sh can wait forever for DONE
- **Proposed resolution**: Install the sentinel after each script's final EXIT trap, or implement a shared composable trap stack and migrate later trap assignments to it; add regression tests where a trap installed after the sentinel still preserves DONE

### FINDING_55:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: <TMPDIR>/plan.txt:127-129; scripts/run-step5-review.sh:1-14; skills/implement/scripts/run-step2-dispatch.sh:1-13
- **Concern**: Two denylisted scripts do not have larch_quiet_init for the planned one-line sentinel insertion. Scenario: run-step5-review.sh and run-step2-dispatch.sh currently do not source lib-quiet.sh or call larch_quiet_init, so the proposed larch_quiet_install_done_sentinel call has no defined insertion point and would be undefined unless more setup is added
- **Proposed resolution**: Explicitly add lib-quiet sourcing and larch_quiet_init to those scripts, with tests for preserved stdout/stderr contracts, or exempt them from the in-script sentinel and use a wrapper-owned DONE sentinel

### FINDING_56:
- **Reviewer(s)**: unknown-slot
- **Severity**: latent
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:44-53,150-154; scripts/lint-bash32.sh:62-90
- **Concern**: Test plan does not actually confirm Bash 3.2 execution of the fallback mechanics. Scenario: The plan says it reuses make lint-bash32, but the current lint-bash32 only statically scans forbidden tokens and cannot validate wc -c offset parsing, side-file updates, trap behavior, or macOS tail/wc semantics
- **Proposed resolution**: Add executable test-breadcrumb-monitor.sh cases for offset parsing, partial lines, truncation, absent stream creation, final drain after DONE, and future EXIT-trap composition under real Bash 3.2 when available; keep lint-bash32 as only the static compatibility gate

### FINDING_57:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: <TMPDIR>/plan.txt:16,71-73
- **Concern**: Lint rewrite contradicts itself on requiring both launch and monitor pairing. Scenario: Approach says run_in_background true and breadcrumb-monitor are both required, but the file-level spec says the structural check requires either run_in_background true or breadcrumb-monitor; an implementation following the latter would pass unpaired launches or orphan monitors
- **Proposed resolution**: Revise scripts/lint-foreground-markers.sh spec and tests so each denylisted anchor requires both run_in_background true in the launch fence and breadcrumb-monitor.sh --task-id in the same or allowed adjacent fence

### FINDING_58:
- **Reviewer(s)**: Codex-dyn-monitor-shell-bridge
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:12,34-35; agent-lint.toml:28-35; AGENTS.md:56
- **Concern**: Plan depends on an undocumented Bash-to-Monitor bridge. Scenario: The repo only documents Monitor as a first-party Claude Code tool and has no confirmed monitor:start shell protocol or harness task-id sentinel path, so breadcrumb-monitor.sh may be unable to activate its primary path or wait on --task-id
- **Proposed resolution**: Make the Bash wc-offset follower the primary implemented path unless a documented Claude Code shell bridge is added; if Monitor remains primary, specify the exact invocation protocol, detection probe, failure signal, and test fixture

### FINDING_59:
- **Reviewer(s)**: Codex-dyn-monitor-shell-bridge
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:11-12,32-37,61,127-129
- **Concern**: Completion and exit-status channel is incomplete. Scenario: The launch step only names LARCH_BREADCRUMB_STREAM, while the sentinel helper only touches LARCH_DONE_SENTINEL and the monitor argv has no --done-sentinel or --status-file; without a repo-confirmed harness task-id sentinel, the monitor cannot know completion or print STATUS=<exit_code>
- **Proposed resolution**: Add explicit per-launch done and status paths, export them before the background launch, pass them to breadcrumb-monitor.sh, and have the EXIT trap capture rc=$? before writing both files

### FINDING_60:
- **Reviewer(s)**: Codex-dyn-monitor-shell-bridge
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:35,47,61,135,144
- **Concern**: The wc -c fallback does not specify complete-record offset handling. Scenario: If the reader snapshots byte growth while a writer is mid-printf, it can advance the side-file bookmark past an incomplete line and later drop or split the remainder; the PIPE_BUF rationale does not prove atomic regular-file append visibility
- **Proposed resolution**: Define the fallback algorithm to advance the bookmark only through the last complete newline, retain incomplete tail bytes for the next poll, detect truncation/rotation when size shrinks, and test partial-line writes explicitly

### FINDING_61:
- **Reviewer(s)**: Codex-dyn-monitor-shell-bridge
- **Severity**: latent
- **Focus area**: correctness
- **Location**: plan.txt:47,51,144
- **Concern**: DONE-sentinel timing claim conflicts with fallback cadence. Scenario: The test plan says DONE sentinel observed exits within 1 second, but the fallback latency is specified as default 2s polling; on macOS there is no inotify-style wakeup in the proposed wc-c loop, so the assertion can fail by design
- **Proposed resolution**: Set sentinel polling cadence to <=1s when using the fallback or relax the test and user-facing claim to the configured polling interval plus scheduling slack

### FINDING_62:
- **Reviewer(s)**: Codex-dyn-monitor-shell-bridge
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:42,52,133
- **Concern**: Foreground-duplication guard uses an inherited env var that can suppress the monitor in the normal background case. Scenario: The parent sets LARCH_QUIET_BREADCRUMBS_ALREADY_SURFACED unconditionally before launch, but lib-quiet.sh unsetting it inside the child cannot mutate the parent environment inherited by the subsequent monitor process, so breadcrumb-monitor.sh may exit silently every time
- **Proposed resolution**: Replace the inherited-env guard with an observable child-written marker file or clear the variable before invoking breadcrumb-monitor.sh; add tests for foreground and background launch paths

### FINDING_63:
- **Reviewer(s)**: Codex-dyn-monitor-shell-bridge
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: plan.txt:53,151,154; scripts/lint-bash32.sh:68-85; Makefile:907-908
- **Concern**: Bash 3.2 portability is asserted but not dynamically confirmed for the new fallback. Scenario: The existing lint-bash32 target is a static token scan and cannot prove wc-c offset bookkeeping, trap EXIT composition, or read-loop behavior under Bash 3.2; the plan’s “bash --version 3.2 fixture in CI” is not backed by current wiring
- **Proposed resolution**: Add a dynamic test-breadcrumb-monitor case that runs under /bin/bash 3.2 when available, skips loudly otherwise, and separately pins fallback offset bookkeeping plus larch_quiet_install_done_sentinel trap composition

### FINDING_64:
- **Reviewer(s)**: Codex-dyn-monitor-shell-bridge
- **Severity**: latent
- **Focus area**: architecture
- **Location**: plan.txt:40-42,47,144
- **Concern**: scripts/breadcrumb-monitor.md lacks an observable primary-vs-fallback activation contract. Scenario: The plan says the sibling doc will mention Monitor vs fallback but does not require it to state which path is primary, how Monitor availability or >10s lag is detected, or how tests know which mode produced near-instant output
- **Proposed resolution**: Require breadcrumb-monitor.md to define a mode-selection state machine, observable diagnostics such as MODE=monitor or MODE=fallback in test mode, activation thresholds, and which latency assertions apply to each mode

### FINDING_65:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/shared/external-reviewers.md:44-51; skills/research/references/research-phase.md:188-195; skills/research/references/validation-phase.md:182-189
- **Concern**: Rewrite surface omits three skill/reference files that still contain the old foreground banner/comment around collect-agent-results.sh. Scenario: After the proposed lint flips hard-fail, these tracked skill/reference Markdown files either fail CI for stale foreground markers or continue teaching agents to foreground a script the plan says must background plus monitor
- **Proposed resolution**: Add these three files explicitly to the plan rewrite target list and convert each collect-agent-results.sh block to the new background pair required banner/comment plus breadcrumb-monitor.sh consumer

### FINDING_66:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: code-quality
- **Location**: scripts/test-lint-foreground-markers.sh:86-99
- **Concern**: Migration-negative test is under-specified. Scenario: The plan only requires an old foreground banner with no paired consumer to fail, which can pass for the wrong reason: missing consumer rather than stale old-marker rejection; it also does not separately exercise the old per-anchor comment
- **Proposed resolution**: Add fixtures where the old banner and old comment appear with an otherwise valid run_in_background true plus breadcrumb-monitor.sh pair, expect non-zero, and assert stderr names the foreground-marker migration or stale old phrase

### FINDING_67:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-implement-anti-polling-rule.sh:53-75
- **Concern**: Existing harness still pins Step 5 foreground behavior and rejects run_in_background true outside Foreground-required banners. Scenario: The plan rewrites Step 5 / Family B calls to intentional background plus monitor, so this harness will fail once skills/implement/SKILL.md contains the new contract
- **Proposed resolution**: Update the harness in the plan: assert paired breadcrumb-monitor usage for Step 5 and continue rejecting unpaired polling loops, instead of requiring one foreground review-and-fix call and filtering by Foreground required

### OOS_1:
- **Description**: If the migration lint literally bans old phrases in all tracked Markdown, committed run logs already contain many stale old-marker literals. Scenario: A repo-wide tracked-Markdown stale-phrase check would fail on archival larch-logs even after authoring files are migrated
- **Reviewer**: unknown-slot
- **Severity**: latent
- **Focus area**: architecture
- **Location**: larch-logs/implement/31B08CAB-9F43-4519-AA5D-7A9FE92A6AC3/plan-goals-test.md:22-31; larch-logs/design/35557933-4A6B-4989-982E-F1E871A8A0D8/plan.txt:18
- **Phase**: design

### FINDING_68:
- **Reviewer(s)**: Codex-dyn-lint-migration-scope
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/shared/external-reviewers.md:44-48; skills/research/references/research-phase.md:188-192; skills/research/references/validation-phase.md:182-186
- **Concern**: Explicit rewrite list misses three current old foreground-marker callsites. Scenario: After lint is repurposed to reject old foreground phrasing, these tracked skill/reference Markdown files still contain the old banner/comment around collect-agent-results.sh and make make lint-foreground-markers fail
- **Proposed resolution**: Add these three files to the plan's rewrite targets and convert each collect-agent-results.sh example to the new background plus breadcrumb-monitor pair

### FINDING_69:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:131-133,scripts/lib-quiet.sh:70-75
- **Concern**: FINDING 1: The foreground-duplication guard relies on child-to-sibling env mutation. Scenario: Parent exports LARCH_QUIET_BREADCRUMBS_ALREADY_SURFACED before launching both siblings; the child unsetting it cannot affect breadcrumb-monitor.sh, so the monitor always inherits 1 and exits silently, including the intended background case
- **Proposed resolution**: Replace the env mutation with a per-launch sentinel file such as LARCH_BREADCRUMBS_SURFACED_SENTINEL; have lib-quiet.sh create it only when FD 3 is actually harness-visible, and have breadcrumb-monitor.sh suppress output only when that file exists

### FINDING_70:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: <TMPDIR>/plan.txt:131-133
- **Concern**: FINDING 2: The foreground-duplication test validates the broken always-silent path. Scenario: The planned test says LARCH_QUIET_BREADCRUMBS_ALREADY_SURFACED=1 should make the helper print nothing; because the proposed parent sets that var before every launch, this assertion would pass while all background breadcrumbs are suppressed
- **Proposed resolution**: Add sibling-process tests: background launch with no surfaced sentinel must print stream lines; foreground/harness-visible case with the surfaced sentinel must print nothing; inherited env alone must not suppress

### FINDING_71:
- **Reviewer(s)**: unknown-slot
- **Severity**: latent
- **Focus area**: architecture
- **Location**: <TMPDIR>/plan.txt:138-140,scripts/lib-quiet.md:50-59
- **Concern**: FINDING 3: New env-var reset and nested-inheritance semantics are underspecified. Scenario: The plan says lib-quiet.md will document the four new vars and increment LARCH_BC_DEPTH in larch_quiet_init, but does not define launch reset, invalid-depth normalization, same-PID idempotent init behavior, stale stream cleanup after monitor launch, or how disable mode affects inherited stream vars
- **Proposed resolution**: Add an explicit env table to scripts/lib-quiet.md: who sets each var, whether it is exported to child trees or monitor siblings, how it is reset after a launch, how nested larch_quiet_init increments depth only for a new PID, and how LARCH_QUIET_DISABLE=1 bypasses all new side effects

### FINDING_72:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:137-150,scripts/lib-quiet.sh:37-42,scripts/lib-quiet.sh:114-124,scripts/test-lib-quiet.sh:49-53
- **Concern**: FINDING 4: LARCH_QUIET_DISABLE coverage is not confirmed for the new breadcrumb-stream target. Scenario: Current disable tests only cover legacy stdout; if the proposed stream append is added inside emit_breadcrumb without checking LARCH_QUIET_DISABLE, disabled harnesses with LARCH_BREADCRUMB_STREAM inherited can still write structured records
- **Proposed resolution**: Add a test with LARCH_QUIET_DISABLE=1 and LARCH_BREADCRUMB_STREAM set, call larch_quiet_init and emit_breadcrumb, and assert no stream file content is produced; implement the disable guard in emit_breadcrumb itself, not only in larch_quiet_init

### FINDING_73:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: code-quality
- **Location**: <TMPDIR>/plan.txt:127-129,scripts/ci-wait.sh:67-70,scripts/ci-wait.sh:170-170,scripts/collect-agent-results.sh:184-184,scripts/collect-agent-results.sh:307-307,skills/implement/scripts/step2-implement.sh:70-70,skills/implement/scripts/step2-implement.sh:402-402
- **Concern**: FINDING 5: Installing the done-sentinel trap immediately after larch_quiet_init can be overwritten later. Scenario: Several target scripts install EXIT traps after larch_quiet_init; the plan adds larch_quiet_install_done_sentinel immediately after init, so later trap assignments in ci-wait.sh, collect-agent-results.sh, and step2-implement.sh can clobber the sentinel touch
- **Proposed resolution**: Revise the plan to chain at each existing EXIT trap site or require larch_quiet_install_done_sentinel after the final trap installation; add regression cases for scripts with traps installed after quiet init

### FINDING_74:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: security
- **Location**: <TMPDIR>/plan.txt:146-146,docs/run-logs.md:3-5,docs/run-logs.md:64-76,scripts/lib-quiet.sh:114-124
- **Concern**: FINDING 6: The plan commits breadcrumb stream files but only redacts monitor stdout. Scenario: The proposed lib-quiet.sh stream writer appends raw emit_breadcrumb text, while breadcrumb-monitor.sh redacts only as it prints; docs/run-logs.md says committed session artifacts are redacted, so committing raw breadcrumb streams can leak secrets despite safe chat output
- **Proposed resolution**: Either do not commit breadcrumb streams, or define a redaction step before persistence; if streams are described as already-redacted, make the writer or log-publish path enforce that and fail closed on redaction failure

### FINDING_75:
- **Reviewer(s)**: Codex-dyn-env-signal-coherence
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:40-52,131-140
- **Concern**: Foreground-duplication signal is specified as a sibling-inherited env var that the child later unsets. Scenario: A child unset of LARCH_QUIET_BREADCRUMBS_ALREADY_SURFACED cannot alter breadcrumb-monitor.sh's already-inherited environment, so the monitor always sees the guard as set and exits silently for background launches too
- **Proposed resolution**: Replace the mutable env signal with a per-launch sentinel file side channel, e.g. export a sentinel path to both siblings and have lib-quiet.sh touch it only when FD-3 is actually surfaced; breadcrumb-monitor.sh should check that file before replaying stream content

### FINDING_76:
- **Reviewer(s)**: Codex-dyn-env-signal-coherence
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:44-53
- **Concern**: The planned foreground-duplication test validates the broken env-var behavior. Scenario: The case “when LARCH_QUIET_BREADCRUMBS_ALREADY_SURFACED=1, the helper prints nothing” would pass even though every real background launch is silenced by the inherited variable
- **Proposed resolution**: Update the test to model the correct side channel: no sentinel means stream breadcrumbs are printed, sentinel present means the monitor exits cleanly, and a child-only unset must not be part of the contract

### FINDING_77:
- **Reviewer(s)**: Codex-dyn-env-signal-coherence
- **Severity**: important
- **Focus area**: architecture
- **Location**: <TMPDIR>/plan.txt:59-65,127-129,140; scripts/lib-quiet.sh:37-76; scripts/lib-quiet.md:50-59
- **Concern**: The four new env vars do not have complete reset and inheritance semantics for nested larch_quiet_init. Scenario: The plan says nested helpers inherit LARCH_BREADCRUMB_STREAM, increments LARCH_BC_DEPTH in larch_quiet_init, and documents the vars, but does not specify per-launch cleanup, same-PID re-init behavior, disabled-mode behavior, or which vars must not leak into later launch pairs
- **Proposed resolution**: Document exact semantics in scripts/lib-quiet.md and implement tests: LARCH_BREADCRUMB_STREAM is inherited only for the active launch pair then unset/restored, LARCH_BC_DEPTH increments once per new PID and never on same-PID idempotent init, LARCH_DONE_SENTINEL is top-level-owned or token-guarded, and LARCH_QUIET_BREADCRUMBS_ALREADY_SURFACED is replaced or scoped as a sentinel-file path

### FINDING_78:
- **Reviewer(s)**: Codex-dyn-env-signal-coherence
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:23,61,127-129; skills/implement/scripts/run-step2-dispatch.sh:88-104; scripts/run-step5-review.sh:179-240
- **Concern**: LARCH_DONE_SENTINEL inheritance can make nested denylisted helpers mark the parent launch complete early. Scenario: The plan adds larch_quiet_install_done_sentinel to all nine denylisted scripts, but run-step2-dispatch.sh invokes step2-implement.sh and run-step5-review.sh invokes review-and-fix.sh; if the same LARCH_DONE_SENTINEL is inherited, the inner helper can touch it while the outer script is still running and breadcrumb-monitor.sh can stop too soon
- **Proposed resolution**: Make the done sentinel per launched top-level task, not blindly inherited by nested helpers; pass an ownership token or clear/rebind LARCH_DONE_SENTINEL before invoking nested denylisted scripts, and add a regression where an inner denylisted script exits before the outer script continues emitting breadcrumbs

### FINDING_79:
- **Reviewer(s)**: Codex-dyn-env-signal-coherence
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: <TMPDIR>/plan.txt:23,127-129; skills/implement/scripts/run-step2-dispatch.sh:1-9,71-104; scripts/run-step5-review.sh:1-9,239-240
- **Concern**: The “add one-line sentinel after larch_quiet_init” step is incomplete for wrappers that do not call larch_quiet_init. Scenario: run-step2-dispatch.sh and run-step5-review.sh currently do not source scripts/lib-quiet.sh or call larch_quiet_init, so the proposed one-line insertion point does not exist and those background launches may lack quiet setup and done-sentinel installation
- **Proposed resolution**: Explicitly add source scripts/lib-quiet.sh plus larch_quiet_init to these wrappers, then install the sentinel after init, or exclude them from sentinel ownership and monitor their child process through a separately specified mechanism

### FINDING_80:
- **Reviewer(s)**: Codex-dyn-env-signal-coherence
- **Severity**: latent
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:67-69,138,148-154; scripts/test-lib-quiet.sh:49-53
- **Concern**: The LARCH_QUIET_DISABLE regression is not specified to cover the new stream target. Scenario: The existing disable test only checks legacy stdout/stderr with no LARCH_BREADCRUMB_STREAM set, and the proposed test list does not require LARCH_QUIET_DISABLE=1 plus LARCH_BREADCRUMB_STREAM; a new stream write path could still emit breadcrumbs while disabled
- **Proposed resolution**: Add a test that sets LARCH_QUIET_DISABLE=1, LARCH_BREADCRUMB_STREAM to a writable file, and emits a breadcrumb, then asserts stdout/stderr remain legacy-compatible and the stream file is absent or empty
