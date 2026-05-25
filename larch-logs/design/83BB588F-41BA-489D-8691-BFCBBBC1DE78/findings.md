### FINDING_1:
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/larch-log.sh:229-259
- **Concern**: Items 5–6 add breadcrumbs batch machinery but no in-scope caller invokes it. Scenario: Per-run files under `$IMPLEMENT_TMPDIR/breadcrumbs/` or `$DESIGN_TMPDIR/breadcrumbs/` are never published; `larch-log commit` never stages `larch-logs/<skill>/<run-id>/breadcrumbs/` despite architecture expecting redacted committed copies
- **Proposed resolution**: Add explicit wiring: e.g. `scripts/refresh-run-logs.sh` and/or `scripts/ship-pr.sh` pre-commit path call `larch-log.sh write --batch breadcrumbs --input-dir "$IMPLEMENT_TMPDIR/breadcrumbs"`; `scripts/design-log-publish.sh` (or design finalize) for `$DESIGN_TMPDIR/breadcrumbs`; document the caller contract in `scripts/larch-log.md`

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-larch-logs-batches.sh:15-57
- **Concern**: Plan updates `larch-log-batches.sh` but not the batch-table regression harness. Scenario: Adding `breadcrumbs / replace breadcrumb-streaming` breaks CI: list drift (line 44–48), extension `/` fails the allowed-extension case (line 54), sanitizer `breadcrumb-streaming` fails the allowed-sanitizer case (line 56)
- **Proposed resolution**: Extend this PR: add `breadcrumbs` to `expected`, allow extension `/` (or dedicated case), allow sanitizer `breadcrumb-streaming` (or map batch to `none` if per-file validation lives only in `larch-log.sh`)

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lib-larch-log.sh:98-168
- **Concern**: New sanitizer `breadcrumb-streaming` has no `case` arm. Scenario: Any code path that calls `larch_log_validate_batch_payload breadcrumbs` dies with `unknown sanitizer for breadcrumbs: breadcrumb-streaming` (directory writer must skip batch-level validate or add a sanitizer that accepts per-file NDJSON lines)
- **Proposed resolution**: Either register a `breadcrumb-streaming` arm (line-level NDJSON/`larch:bc` checks) or use sanitizer `none` and validate each redacted file inside the new `--input-dir` branch before atomic write

### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: security
- **Location**: scripts/larch-log.sh:130-135
- **Concern**: Symlink guard names only `$DESIGN_TMPDIR`. Scenario: Implement/review runs store streams under `$IMPLEMENT_TMPDIR/breadcrumbs/`; escape checks keyed only on `DESIGN_TMPDIR` miss the primary surface or false-reject implement paths
- **Proposed resolution**: Pass `--session-tmpdir` (or derive from `--input-dir`) and require `realpath` under `IMPLEMENT_TMPDIR`, `DESIGN_TMPDIR`, or `REVIEW_TMPDIR`; align Edge case #6 (`[ -L "$file" ]` only) with the main symlink paragraph—drop `readlink` follow

### FINDING_5:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/larch-log.sh:130-134
- **Concern**: Per-file redactor failure logging omits session tmpdir for `append-tool-failure.sh`. Scenario: Skip+warn path must append to `$<SKILL>_TMPDIR/execution-issues.md`; `larch-log.sh` only receives `--log-root` today, so warnings may go nowhere or to the wrong file
- **Proposed resolution**: Accept `--session-tmpdir` (or `--execution-issues-md`) on the breadcrumbs write branch and call `append-tool-failure.sh --log "$session_tmpdir/execution-issues.md"` with site `larch-log breadcrumbs batch` per plan

### FINDING_6:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ci-wait.sh:183-281
- **Concern**: `larch_errf` → `emit_breadcrumb` changes FD contract when stream env is unset. Scenario: `larch_errf` uses restored stderr (`>&4` after quiet init); `emit_breadcrumb` without `LARCH_BREADCRUMB_STREAM` falls through to stdout (quiet log). Residual synchronous callers lose stderr-visible dots/progress
- **Proposed resolution**: Keep `larch_errf` when `LARCH_BREADCRUMB_STREAM` is unset; only migrate lines when stream is set (or add `emit_breadcrumb_stderr` helper matching `larch_errf` semantics)

### FINDING_7:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: <TMPDIR>/plan.txt:135-136 vs plan.txt:191
- **Concern**: Plan contradicts itself on symlink detection. Scenario: Implementer may `readlink`+follow (violates Edge case #6) or skip only symlinks while missing hardlink/escape cases
- **Proposed resolution**: Normalize plan text: `[ -L "$file" ]` skip only; optional `realpath` containment vs session tmpdir; no `readlink` follow

### FINDING_8:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: nit
- **Focus area**: architecture
- **Location**: <TMPDIR>/plan.txt:145-156
- **Concern**: Planned `breadcrumb-monitor.md` exit codes do not match `scripts/breadcrumb-monitor.sh`. Scenario: Doc specifies exit 1 on redactor non-zero and exit 3 on path rejection; script validates paths with exit 2, times out with exit 4, suppresses redact failures per-line, and always `exit 0` at line 216
- **Proposed resolution**: Author `.md` from observed behavior: exit 2 argv/setup+path, exit 4 monitor timeout, exit 0 normal; document per-line `WARN redact-drop-line` not process-level exit 1

### FINDING_9:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: nit
- **Focus area**: architecture
- **Location**: <TMPDIR>/plan.txt:158-167
- **Concern**: Planned `lib-redact-streaming.md` describes non-existent function API. Scenario: `scripts/lib-redact-streaming.sh` is a CLI wrapper (`--state-file`, stdin/stdout loop), not `larch_redact_stream_*` functions
- **Proposed resolution**: Document script invocation and exit codes (0 success, 1 redactor line failure, 2 missing state); drop function-entry-point section or point to `redact-secrets.sh --streaming`

### FINDING_10:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: scripts/collect-agent-results.sh:156-171
- **Concern**: Category migration must preserve `>&2` redirection on two callsites. Scenario: `emit_breadcrumb "…" >&2` redirects the function’s stdout; dropping `>&2` during `--category=` migration can change wait-loop diagnostics
- **Proposed resolution**: Keep `>&2` (or equivalent) when adding `--category=progress|retry|…` immediately after `emit_breadcrumb`

### FINDING_11:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: nit
- **Focus area**: risk-integration
- **Location**: scripts/ship-pr.sh:2445-2447
- **Concern**: `larch_quiet_append_done_trap` placement is underspecified for a trap-less script. Scenario: `ship-pr.sh` has no `trap … EXIT`; calling the helper only inside `main()` after `larch_quiet_init` is correct, but “after last trap” wording invites a wrong EOF placement
- **Proposed resolution**: State explicitly: in `main()` immediately after `larch_quiet_init` (line 2446); no prior EXIT trap to chain

### FINDING_12:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: latent
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:205
- **Concern**: Spot-check grep may miss valid uncategorized callsites. Scenario: Pattern `grep -v 'emit_breadcrumb.*--category='` false-negatives split-line invocations and may false-positive comment lines
- **Proposed resolution**: Add `make`/harness check or `rg -U` multiline scan; exclude `scripts/test-*.sh` fixtures intentionally

### FINDING_13:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lib-quiet.sh:149-155; scripts/ci-wait.sh:170; plan.txt:22-25
- **Concern**: Done-trap plan assumes writer then sentinel, but larch_quiet__exit_combo writes the new done sentinel before evaling the prior EXIT trap. Scenario: The foreground monitor can observe LARCH_DONE_SENTINEL before ci-wait.sh has written its OUTPUT_FILE and .done sidecar; prior traps that capture $? also see the status of larch_quiet__exit_write_done instead of the script exit
- **Proposed resolution**: Revise the plan to change lib-quiet.sh trap chaining so the saved prior EXIT trap runs with the original exit status before larch_quiet__exit_write_done touches LARCH_STATUS_FILE and LARCH_DONE_SENTINEL, then add/adjust test-lib-quiet coverage

### FINDING_14:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:128-135; scripts/larch-log-flush.sh:25-49
- **Concern**: The breadcrumbs batch has no proposed caller that stages it before larch-log commit. Scenario: Adding larch-log.sh write support and a batch-table row alone leaves no persisted breadcrumbs because existing flush paths only flush execution issues and commit whatever is already staged
- **Proposed resolution**: Add a concrete flush call in the relevant lifecycle paths, for example larch-log-flush.sh / refresh-run-logs.sh / design finalization as applicable, invoking larch-log.sh write --batch breadcrumbs --input-dir "$<SKILL>_TMPDIR/breadcrumbs" before commit

### FINDING_15:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: security
- **Location**: plan.txt:130-135; skills/design/references/plan-review.md:97-104
- **Concern**: The proposed directory walk commits every regular file in breadcrumbs/, but that directory also contains status, done, quiet-log, surfaced-sentinel, and monitor state files. Scenario: Committed run logs would include non-breadcrumb control artifacts and quiet logs; quiet logs are larger, less structured, and may contain sensitive or irrelevant process output despite best-effort redaction
- **Proposed resolution**: Limit the batch to breadcrumb stream files, e.g. known *.ndjson stream basenames or files whose records validate as larch:bc, and explicitly exclude *.done.*, *.status.*, *.quiet.*, *.surfaced.*, *.bc-offset, and redactor state files

### FINDING_16:
- **Reviewer(s)**: Codex-Arch
- **Severity**: latent
- **Focus area**: correctness
- **Location**: .claude/skills/bump-version/scripts/apply-bump.sh:195; scripts/ship-pr.sh:928
- **Concern**: Stream-category migration omits apply-bump.sh even though ship-pr.sh invokes it while inheriting the breadcrumb stream. Scenario: On an origin/main version collision, apply-bump.sh emits an uncategorized breadcrumb, lib-quiet drops it from LARCH_BREADCRUMB_STREAM, and the operator loses retry visibility while seeing unknown-category warnings
- **Proposed resolution**: Add .claude/skills/bump-version/scripts/apply-bump.sh to the migration with --category=retry and expand the verification grep to include .claude/skills

### FINDING_17:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lib-quiet.sh:48-87; scripts/run-step5-review.sh:239-240; skills/implement/scripts/run-step2-dispatch.sh:104
- **Concern**: Plan adds larch_quiet_init to stdout relay wrappers without preserving child contract stdout. Scenario: larch_quiet_init redirects ordinary stdout/stderr to the quiet log; the wrapper then invokes review-and-fix.sh or step2-implement.sh, so child KV envelopes are inherited into the quiet log instead of the orchestrator-visible stream
- **Proposed resolution**: For these relay wrappers, source lib-quiet.sh without larch_quiet_init and call larch_quiet_append_done_trap directly, or explicitly run the child with stdout/stderr restored to FD3/FD4 while keeping the done trap

### FINDING_18:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lib-quiet.sh:149-155; scripts/ci-wait.sh:170
- **Concern**: Done sentinel fires before the preserved EXIT trap despite the plan claiming writer -> done order. Scenario: breadcrumb-monitor exits when LARCH_DONE_SENTINEL is touched, but ci-wait.sh's existing .done writer or collect-agent-results cleanup runs only afterward, creating a race where downstream readers see completion before sidecars/cleanup are complete
- **Proposed resolution**: Change larch_quiet__exit_combo to run LARCH_QUIET_PREV_EXIT_TRAP first while preserving the original exit code, then write LARCH_STATUS_FILE and touch LARCH_DONE_SENTINEL

### FINDING_19:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/design-log-publish.sh:257-322; scripts/refresh-run-logs.sh:75-80
- **Concern**: Breadcrumb batch support has no proposed caller that actually flushes the batch. Scenario: Adding larch-log.sh --batch breadcrumbs support does not persist anything unless design/implement publish paths invoke it; current publish code stages top-level files/render-cache or token/timing batches, so breadcrumb streams remain tmpdir-only and are lost on cleanup
- **Proposed resolution**: Add explicit breadcrumbs flush calls at each committed-log publish path before commit/publish, including design-log-publish.sh and implement refresh/finalize/ship paths, and re-flush execution issues after any breadcrumb warnings are appended

### FINDING_20:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: security
- **Location**: <TMPDIR>/plan.txt:132-133
- **Concern**: Streaming redaction writes directly to the committed destination before success is known. Scenario: If redact-secrets.sh --streaming writes partial output and then exits non-zero, the plan's skip contract is violated and a partial breadcrumb file may remain under larch-logs/<run-id>/breadcrumbs/
- **Proposed resolution**: Redirect redactor output to a temp file in the destination directory, remove it on failure, and atomically mv into place only after redactor success

### FINDING_21:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:131-135
- **Concern**: Hardcoded DESIGN_TMPDIR escape check conflicts with analogous per-skill tmpdirs. Scenario: Implement/review callers will use IMPLEMENT_TMPDIR or REVIEW_TMPDIR breadcrumbs; with set -u, referencing DESIGN_TMPDIR when unset can abort, and checking escapes only against DESIGN_TMPDIR can skip valid files from other skills
- **Proposed resolution**: Validate --input-dir by canonicalizing the input directory and deriving the allowed root from DESIGN_TMPDIR, IMPLEMENT_TMPDIR, or REVIEW_TMPDIR, then require each regular file's real path to stay under that canonical input root

### FINDING_22:
- **Reviewer(s)**: Codex-Edge
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: <TMPDIR>/plan.txt:203-205
- **Concern**: Spot-check grep includes non-callsite files and the emit_breadcrumb definition. Scenario: The proposed zero-uncategorized check will still match scripts/lib-quiet.sh, docs, and test fixtures, causing a false failure or encouraging broad accidental edits
- **Proposed resolution**: Narrow the check to runtime caller files only, exclude scripts/lib-quiet.sh and test/doc files, or use an AST/simple shell-aware allowlist of the migrated files

### FINDING_23:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/design-log-publish.sh:257-322
- **Concern**: Items 5–6 add larch-log breadcrumbs writer but no publish caller is specified. Scenario: $DESIGN_TMPDIR/breadcrumbs/*.ndjson are created during background+monitor runs but design-log-publish only stages maxdepth-1 files plus render-cache; implement has no Step 7a/refresh-run-logs write either — committed larch-logs never gain breadcrumbs/ despite batch registry
- **Proposed resolution**: Wire publish: call larch-log.sh write --batch breadcrumbs --input-dir "$DESIGN_TMPDIR/breadcrumbs" from design-log-publish.sh (and IMPLEMENT_TMPDIR analogue in Step 7a / refresh-run-logs.sh) with best-effort partial-success semantics matching the plan

### FINDING_24:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lib-quiet.sh:149-177; scripts/ci-wait.sh:160-170
- **Concern**: F1 Proposed done-trap placement relies on prior EXIT traps running before the LARCH done sentinel, but larch_quiet__exit_combo currently writes LARCH_STATUS_FILE/LARCH_DONE_SENTINEL before evaling the saved trap and does not preserve $? for the saved trap. Scenario: ci-wait can publish the new done sentinel before its existing output-file trap runs, and the existing trap may capture the wrong exit status; monitors or consumers can race on incomplete sidecars
- **Proposed resolution**: Change lib-quiet in this PR so the saved EXIT body runs first with $? primed to the original exit code, then write LARCH_STATUS_FILE and LARCH_DONE_SENTINEL; add a focused Bash 3.2 trap-chain regression

### FINDING_25:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: code-quality
- **Location**: scripts/lib-quiet.sh:48-86; scripts/run-step5-review.sh:11-21; skills/implement/scripts/run-step2-dispatch.sh:6-13
- **Concern**: F2 The plan assumes larch_quiet_init is inert for new adopters, but it redirects stdout/stderr by default and the target wrappers still use raw printf >&2 diagnostics. Scenario: Adding larch_quiet_init near the top of run-step5-review.sh or run-step2-dispatch.sh hides usage/errors in the quiet log and triggers S041 no-raw-stderr-after-quiet-init lint failures
- **Proposed resolution**: Use a narrower helper path: source lib-quiet.sh and call larch_quiet_append_done_trap without larch_quiet_init, or convert every diagnostic to larch_err/larch_errf and make stdout/stderr byte-shape tests in-scope for these two adopters

### FINDING_26:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:1533-1582; scripts/refresh-run-logs.sh:61-95; scripts/larch-log-flush.sh:30-48
- **Concern**: F3 The plan adds a breadcrumbs batch writer but does not wire any existing log-flush path to call it before larch-log commit. Scenario: After the PR, larch-log.sh may support --input-dir, but implement runs still commit token/timing/session/execution batches only, so breadcrumb streams remain session-local and disappear at cleanup
- **Proposed resolution**: Add explicit larch-log.sh write --batch breadcrumbs --input-dir "$IMPLEMENT_TMPDIR/breadcrumbs" calls in Step 7a, refresh-run-logs.sh, and larch-log-flush.sh before commit, with a post-warning execution-issues flush when warnings are generated

### FINDING_27:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: security
- **Location**: scripts/larch-log.sh:229-258; scripts/append-tool-failure.sh:68-76; docs/run-logs.md:40-41
- **Concern**: F4 The proposed redactor-skip warning path targets execution-issues.md, but larch-log.sh writes committed batches and append-tool-failure emits markdown, not the committed execution-issues.ndjson batch. Scenario: A breadcrumb redaction skip after the Step 7a flush, or in non-implement log publishing, can be logged to the wrong markdown file or never converted into the durable run log
- **Proposed resolution**: Have larch-log.sh append a compact NDJSON execution-issues record through the existing execution-issues batch, or require an explicit --execution-issues-log plus an immediate flush after breadcrumb warnings

### FINDING_28:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/larch-log.sh:229-258; scripts/larch-log-batches.sh:36-57
- **Concern**: F5 Breadcrumb path-scope validation is specified against $DESIGN_TMPDIR even though the batch is meant for implement/review/design tmpdirs. Scenario: Implement breadcrumbs under IMPLEMENT_TMPDIR can be rejected when DESIGN_TMPDIR is unset, or validation becomes inconsistent across skills
- **Proposed resolution**: Accept an explicit --input-root or infer the allowed root from --skill and the input dir; reject a symlink input directory and validate each regular file realpath under that root

### FINDING_29:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/run-step2-dispatch.sh:54-57 skills/implement/scripts/step2-implement.sh:402 skills/review-and-fix/scripts/review-and-fix.sh:10 scripts/run-step5-review.sh:49-50
- **Concern**: Plan wires larch_quiet_append_done_trap on both wrapper and inner denylisted children that share one LARCH_DONE_SENTINEL export. Scenario: Child EXIT can touch the done sentinel and unblock breadcrumb-monitor before the outer wrapper process exits; a later parent trap can overwrite LARCH_STATUS_FILE with a different code
- **Proposed resolution**: Install the done trap only on the backgrounded top-level denylisted PID per launch (wrapper OR direct child), not on both nested scripts in the same invocation chain

### FINDING_30:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lib-quiet.sh:149-177; scripts/ci-wait.sh:160-170
- **Concern**: F1: done-trap preservation assumption is false. Scenario: The plan relies on larch_quiet_append_done_trap preserving existing EXIT traps, but current trap -p parsing does not capture Bash single-quoted trap output, and larch_quiet__exit_combo writes the new done sentinel before any prior trap. Adding it after ci-wait.sh's trap can drop or race the existing ${OUTPUT_FILE}.done writer.
- **Proposed resolution**: Add scripts/lib-quiet.sh to the plan: robustly capture prior EXIT traps, execute prior trap before larch_quiet__exit_write_done while preserving the original exit code, and add focused test-lib-quiet coverage.

### FINDING_31:
- **Reviewer(s)**: Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/lib-quiet.sh:48-87; scripts/run-step5-review.sh:1-238; skills/implement/scripts/run-step2-dispatch.sh:1-109
- **Concern**: F2: larch_quiet_init is not inert for new adopters. Scenario: larch_quiet_init redirects stdout/stderr by default. Adding it to run-step5-review.sh and run-step2-dispatch.sh can hide wrapper diagnostics and child review-and-fix/step2-implement machine KVs in the quiet log instead of returning them to the orchestrator.
- **Proposed resolution**: Do not call larch_quiet_init in those wrapper scripts; source lib-quiet.sh only for the done-trap helper, or introduce a no-redirect done-trap helper. If quiet init is truly required, convert all contract output paths and child FD handling explicitly.

### FINDING_32:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/design-log-publish.sh:254-276; scripts/larch-log-flush.sh:30-50; skills/implement/SKILL.md:662-675
- **Concern**: F3: breadcrumbs batch is not wired into publishers. Scenario: The plan adds a larch-log breadcrumbs writer, but no proposed caller passes --batch breadcrumbs. design-log-publish.sh only stages top-level design tmpdir files, and implement flush mappings do not include breadcrumbs, so breadcrumb streams remain uncommitted.
- **Proposed resolution**: Add publish wiring for each lifecycle path that owns committed logs: design-log-publish should stage or call the breadcrumbs batch for DESIGN_TMPDIR/breadcrumbs, and implement refresh/flush checkpoints should call larch-log.sh write --batch breadcrumbs --input-dir "$IMPLEMENT_TMPDIR/breadcrumbs" when present.

### FINDING_33:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/larch-log.sh:229-259
- **Concern**: F4: path containment is hardcoded to DESIGN_TMPDIR for an analogous per-skill batch. Scenario: The plan says the input dir may be DESIGN_TMPDIR/breadcrumbs or analogous per-skill tmpdirs, but then requires realpath not escape DESIGN_TMPDIR. Implement/review breadcrumb files would be skipped when DESIGN_TMPDIR is unset or different.
- **Proposed resolution**: Validate against the resolved active session root that matches the input dir, selected from DESIGN_TMPDIR, IMPLEMENT_TMPDIR, or REVIEW_TMPDIR, or against the resolved input directory itself. Keep explicit -L rejection before realpath.

### FINDING_34:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/larch-log.sh:229-259; scripts/append-tool-failure.sh:163-166; skills/implement/scripts/flush-execution-issues.sh:169-198
- **Concern**: F5: per-file warning logging target is underspecified. Scenario: append-tool-failure.sh writes Markdown execution-issues.md, while committed execution issues are NDJSON and larch-log.sh does not accept an issue-log path. A redactor failure could be unaudited, or an implementer could accidentally append Markdown to execution-issues.ndjson.
- **Proposed resolution**: Add an explicit --issue-log option or derive the active session tmpdir execution-issues.md, then rely on the existing flush path to convert it to NDJSON. State that append-tool-failure output must never be written directly to execution-issues.ndjson.

### FINDING_35:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:26-27; feature-description.txt:11-12
- **Concern**: ci-wait progress lines planned as --category=progress but issue #2790 item 2 requires --category=wait-ci for progress-tier larch_errf conversions. Scenario: CI wait breadcrumbs use the wrong stream category; operators filtering on wait-ci miss the highest-impact Family-B script surface
- **Proposed resolution**: Relabel plan lines 183-187 and 267-270 (and other CI-wait progress-tier conversions) to wait-ci per issue item 2; reserve progress only where issue text explicitly allows

### FINDING_36:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lib-quiet.sh:149-154
- **Concern**: Done trap currently runs before the prior EXIT trap. Scenario: The plan assumes appending after ci-wait.sh and collect-agent-results.sh traps yields writer or cleanup before the done sentinel, but larch_quiet__exit_combo writes LARCH_DONE_SENTINEL before evaling LARCH_QUIET_PREV_EXIT_TRAP. The foreground monitor can observe done and continue before ci-wait.sh writes its existing .done sidecar or before cleanup runs.
- **Proposed resolution**: Add scripts/lib-quiet.sh to the updated-file list and change larch_quiet__exit_combo to run the captured prior EXIT trap before larch_quiet__exit_write_done while preserving the original exit code, or otherwise implement a helper that truly appends the done sentinel last.

### FINDING_37:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/design-log-publish.sh:266-318; skills/implement/SKILL.md:1516-1582
- **Concern**: Breadcrumbs batch has no publishing callsite. Scenario: The plan adds larch-log.sh support for a breadcrumbs batch, but design-log-publish.sh only stages top-level files and render-cache, and the implement Step 7a/refresh log flush snippets do not call larch-log.sh write for breadcrumbs. The new batch can pass unit checks yet never appear under committed larch-logs.
- **Proposed resolution**: Add explicit publisher updates for design and implement flows to call larch-log.sh write --batch breadcrumbs --input-dir "$TMPDIR/breadcrumbs" before the relevant commit/publish step, including no-directory and partial-failure handling.

### FINDING_38:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: security
- **Location**: scripts/append-tool-failure.sh:76-83; scripts/larch-log.sh:229-252
- **Concern**: Redactor-failure warning contract is underspecified. Scenario: The plan requires per-file streaming-redactor failures to append a Warnings entry, but append-tool-failure.sh requires --log and --output-file and larch-log.sh currently has no --input-dir parent/issue-log resolution in its write parser. A literal implementation cannot satisfy Q4 reliably and may either abort under set -e or drop the audit trail.
- **Proposed resolution**: Specify how larch-log.sh derives the session execution-issues.md path from --input-dir or a new explicit flag, capture redactor stderr/stdout to a temp output file, pass all required append-tool-failure.sh args, and continue even if warning append itself fails.

### FINDING_39:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: nit
- **Focus area**: correctness
- **Location**: scripts/ci-wait.sh:247-256
- **Concern**: ci-wait newline conversion conflicts with the edge-case decision. Scenario: The ci-wait file section says line 248 should become emit_breadcrumb --category=progress, while the edge-case section later says to keep that bare newline on larch_errf unchanged. Implementers following the first instruction will violate the plan's own byte-shape preservation note.
- **Proposed resolution**: Remove line 248 from the conversion list and state that the spot-check either exempts this cosmetic separator or verifies it remains the only intentional larch_errf progress-adjacent line.

### FINDING_40:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: code-quality
- **Location**: scripts/test-lib-quiet.sh:67-82; scripts/lib-quiet.sh:180-186
- **Concern**: The uncategorized-callsite spot-check cannot reach ZERO as written. Scenario: The proposed grep scans scripts/ and skills/*/scripts/ and will still match lib-quiet.sh's function definition plus test helper strings and documentation snippets that are not migrated runtime callsites. The validation step will fail even after the intended migration, or push implementers toward unrelated test/doc churn.
- **Proposed resolution**: Replace the spot-check with a runtime executable allowlist or add precise exclusions for lib-quiet.sh, tests, and .md files; if tests/examples should be updated, list those files explicitly in the plan and expected assertions.

### FINDING_41:
- **Reviewer(s)**: Cursor-dyn-trap-sequencing
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:2446-2582
- **Concern**: Plan cites larch_quiet_init at 2446 but does not require larch_quiet_append_done_trap immediately after it. Scenario: main() has many die_usage/exit paths between init and the phase loop (2471-2561); registering the done-trap only at main EOF skips trap install on early validation exits, leaving breadcrumb-monitor without LARCH_DONE_SENTINEL/LARCH_STATUS_FILE
- **Proposed resolution**: Add one line larch_quiet_append_done_trap immediately after larch_quiet_init at 2446; state explicitly that ship-pr has no script-owned EXIT trap (grep confirms none)

### FINDING_42:
- **Reviewer(s)**: Codex-dyn-trap-sequencing
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lib-quiet.sh:149-154, scripts/ci-wait.sh:170
- **Concern**: Done-trap chaining runs the new done sentinel before the prior EXIT trap and does not preserve $? for the prior trap. Scenario: The proposed ci-wait insertion after line 170 snapshots the writer trap, but larch_quiet__exit_combo first calls larch_quiet__exit_write_done, then evals the saved trap; ci-wait's saved EXIT_STATUS=$? can observe 0 instead of the script failure status, so ${OUTPUT_FILE}.done can report success after CI failure or timeout
- **Proposed resolution**: Change larch_quiet__exit_combo so the saved prior EXIT trap runs before the quiet done sentinel and receives the original exit status, for example by restoring $? immediately before eval; add a regression covering ci-wait failure writing a nonzero ${OUTPUT_FILE}.done after append_done_trap

### FINDING_43:
- **Reviewer(s)**: Codex-dyn-trap-sequencing
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/lib-quiet.sh:48-87, scripts/run-step5-review.sh:240, skills/implement/scripts/run-step2-dispatch.sh:104, skills/implement/scripts/step2-implement.sh:66-70, skills/review-and-fix/scripts/review-and-fix.sh:9-10
- **Concern**: The plan treats larch_quiet_init as inert for the two new adopters, but it redirects stdout and stderr by default before they exec child scripts. Scenario: run-step5-review.sh and run-step2-dispatch.sh currently pass through child contract output; after the proposed larch_quiet_init, the child inherits stdout as the parent's quiet log, so child emit/emit_kv output can disappear from the caller even though no wrapper code was changed
- **Proposed resolution**: For these pass-through wrappers, source lib-quiet.sh but do not call larch_quiet_init before invoking the child; call larch_quiet_append_done_trap directly, or explicitly preserve/restore the original stdout/stderr around the child invocation and test byte-identical output

### FINDING_44:
- **Reviewer(s)**: Cursor-dyn-api-line-drift
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lib-quiet.sh:48-86
- **Concern**: Edge case 1 claims larch_quiet_init is inert with no env vars; init always redirects stdout/stderr to a quiet log unless LARCH_QUIET_DISABLE or the narrow ACTIVE-without-PID early return fires. Scenario: Direct or harness runs of run-step5-review.sh / run-step2-dispatch.sh without the five LARCH_* exports change visible output despite the byte-identical regression deferral
- **Proposed resolution**: Revise edge case 1: init is only no-op for done_trap when sentinels unset; adopters need LARCH_QUIET_DISABLE=1 in harnesses or document that orchestrator-exported LARCH_QUIET_LOG_FILE intentionally redirects; do not equate that with inert init

### FINDING_45:
- **Reviewer(s)**: Codex-dyn-api-line-drift
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lib-quiet.sh:48-87; scripts/lib-quiet.md:14-17; skills/implement/scripts/run-step2-dispatch.sh:6-13,104; skills/implement/scripts/step2-implement.sh:68-70,169-170; scripts/run-step5-review.sh:11-21,206-207,239-240
- **Concern**: larch_quiet_init is not inert without done/status env vars. Scenario: The plan adds source plus larch_quiet_init to pass-through wrappers and relies on byte-identical stdout/stderr, but first init creates a log, binds FD3/FD4, and redirects ordinary stdout/stderr. run-step2-dispatch would invoke step2-implement with stdout already redirected, so the child's emit_kv contract can land in the parent's quiet log instead of the caller; raw usage/fail printf in both wrappers also disappear from stderr.
- **Proposed resolution**: Do not call larch_quiet_init in these pass-through wrappers, or restore original stdout/stderr around child execution; if init is required, convert diagnostics to larch_err/larch_errf and add explicit stdout/stderr contract regression tests before adoption.

### FINDING_46:
- **Reviewer(s)**: Codex-dyn-api-line-drift
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lib-quiet.sh:149-155,159-178; scripts/ci-wait.sh:160-170
- **Concern**: larch_quiet_append_done_trap does not preserve prior EXIT trap status/order. Scenario: The plan says appending after ci-wait's trap yields writer then done-sentinel, but larch_quiet__exit_combo writes the quiet done/status first and only then evals the prior trap. ci-wait's prior trap begins EXIT_STATUS=$?, so it can capture the status of the quiet helper path rather than the script's original exit code, and the quiet done sentinel can appear before ci-wait publishes OUTPUT_FILE and OUTPUT_FILE.done.
- **Proposed resolution**: Revise the plan to use a script-specific combined trap for ci-wait that captures the original exit code once, runs emit_output and OUTPUT_FILE.done publication first, then writes the quiet done/status with that same code; do not rely on generic eval of a saved trap body to preserve $?.

### FINDING_47:
- **Reviewer(s)**: Cursor-dyn-batch-schema-extension
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/larch-log-batches.sh:6-58
- **Concern**: Proposed row `breadcrumbs / replace breadcrumb-streaming` is parsed as slug+file-extension `/`+mode+sanitizer; no directory-batch semantics exist. Scenario: Awk requires NF==4; `larch_log_batch_extension` returns `/`; `larch_log_batch_path` builds a single replace artifact `…/breadcrumbs/` not a directory tree
- **Proposed resolution**: Use a dedicated convention: e.g. extension `.dir` or a new `write-breadcrumbs` verb; teach `larch_log_batch_path`/`exists` to branch on directory batches; document in larch-log-batches.md

### FINDING_48:
- **Reviewer(s)**: Codex-dyn-batch-schema-extension
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-larch-logs-batches.sh:43-57, scripts/lib-larch-log.sh:66-73
- **Concern**: The proposed breadcrumbs / replace breadcrumb-streaming row fits the four-field table parser but invents unsupported directory extension and sanitizer conventions. Scenario: Existing batch consistency checks reject / and breadcrumb-streaming, while generic path helpers treat extension as a file suffix and emit a trailing-slash path with file-oriented semantics
- **Proposed resolution**: Add explicit directory-batch support in helpers/tests/docs, or keep directory batches out of the extension column and handle breadcrumbs through a separate explicit registry

### FINDING_49:
- **Reviewer(s)**: Codex-dyn-batch-schema-extension
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/larch-log.sh:18-24, scripts/larch-log.sh:229-252
- **Concern**: The plan under-specifies the write argument parser changes needed for --input-dir. Scenario: Current write rejects --input-dir as unknown, then requires INPUT_FILE to be a regular file before any batch-specific dispatch can run
- **Proposed resolution**: Update usage, initialize INPUT_DIR, parse --input-dir, enforce exactly one of --input-file/--input-dir, and branch for BATCH=breadcrumbs before file-only validation and larch_log_validate_batch_payload

### FINDING_50:
- **Reviewer(s)**: Codex-dyn-batch-schema-extension
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/design-log-publish.sh:257-322, scripts/refresh-run-logs.sh:74-95, scripts/design-log-publish.sh:54-58
- **Concern**: The plan adds a writer but no caller wiring for breadcrumb directories or the PUBLISH_OK mapping it references. Scenario: /design publish only stages top-level files and render-cache, ignoring DESIGN_TMPDIR/breadcrumbs entirely; implement refresh paths write token/timing/transcript only; PUBLISH_OK exists only in design-log-publish, not larch-log
- **Proposed resolution**: Add explicit calls from design-log-publish and implement flush/refresh points to larch-log.sh write --batch breadcrumbs --input-dir ..., then map partial breadcrumb success to PUBLISH_OK=true only in design-log-publish where that variable exists

### FINDING_51:
- **Reviewer(s)**: Codex-dyn-batch-schema-extension
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/append-tool-failure.sh:68-74, scripts/append-tool-failure.sh:100-103
- **Concern**: The skip-per-file warning contract omits the required failure-output file. Scenario: Plan says append a Warnings entry on redactor failure, but append-tool-failure.sh refuses to run without an existing --output-file, so the audit warning can be lost exactly when redaction fails
- **Proposed resolution**: Capture each failed streaming redactor stderr/stdout into a per-file failure log and pass it as --output-file with --redact; treat warning-append failure as visible stderr or an aggregate larch-log failure

### FINDING_52:
- **Reviewer(s)**: Codex-dyn-batch-schema-extension
- **Severity**: latent
- **Focus area**: security
- **Location**: scripts/larch-log.sh:261-280
- **Concern**: The symlink/escape rule is tied to DESIGN_TMPDIR but larch-log has no source-root argument and existing directory handling validates source dirs explicitly. Scenario: For implement or review tmpdirs, DESIGN_TMPDIR may be unset or wrong; an input directory symlink or wrongly scoped root could make the escape check ineffective or skip all files
- **Proposed resolution**: Add an explicit --input-root/--source-root or derive and validate the resolved input dir, reject input-dir symlinks, and check every emitted file remains under that resolved root before redaction and publish

### FINDING_53:
- **Reviewer(s)**: Cursor-dyn-deferred-ci-gap
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:203-205
- **Concern**: Testing strategy cites issue #2790 acceptance wholesale but omits deferred make test-breadcrumb-monitor targets. Scenario: Implementer or reviewer runs full issue acceptance on the core PR and gets immediate Makefile failures (no phony recipes; see Makefile:4-15 vs absence of test-breadcrumb-monitor)
- **Proposed resolution**: Replace the blanket footnote with an explicit core-PR checklist that excludes item 4/7 targets; cross-link OUT_OF_SCOPE items 4 and 7

### FINDING_54:
- **Reviewer(s)**: Cursor-dyn-deferred-ci-gap
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:125-126
- **Concern**: lib-larch-log.sh sanitizer dispatch not in file list. Scenario: Registering sanitizer breadcrumb-streaming in larch-log-batches.sh without a matching case in lib-larch-log.sh:103-167 makes larch_log_validate_batch_payload fail with unknown sanitizer for $batch if the breadcrumbs writer reuses the standard write path
- **Proposed resolution**: Add scripts/lib-larch-log.sh to UPDATED (new breadcrumb-streaming case as no-op or dedicated hook) or register the batch with sanitizer none and keep redaction wholly in the custom directory-walk branch

### FINDING_55:
- **Reviewer(s)**: Cursor-dyn-deferred-ci-gap
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:26-32
- **Concern**: ci-wait progress categories diverge from issue #2790 item 2. Scenario: Issue item 2 requires emit_breadcrumb --category=wait-ci for progress-tier CI wait lines; plan maps CI waiting/poll lines to progress, weakening wait-ci stream semantics and acceptance traceability
- **Proposed resolution**: Align ci-wait.sh migration lines with issue item 2 (wait-ci for CI-wait progress); document any intentional deviation in the plan Approach section

### FINDING_56:
- **Reviewer(s)**: Cursor-dyn-deferred-ci-gap
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:135-136 vs plan.txt:191
- **Concern**: Symlink handling contradicts between larch-log breadcrumbs spec and Edge case 6. Scenario: larch-log.sh section requires readlink/realpath escape checks; Edge case 6 forbids readlink and mandates only [ -L ] — implementer cannot satisfy both
- **Proposed resolution**: Unify on one contract (prefer [ -L ] plus optional realpath-under-input-dir guard without following symlinks) and update both sections

### FINDING_57:
- **Reviewer(s)**: Cursor-dyn-deferred-ci-gap
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:128-135 vs plan.txt:211-212
- **Concern**: Breadcrumbs batch lands without test-larch-log.sh coverage (deferred item 4). Scenario: Core PR adds committed-log redaction plumbing but defers the test-larch-log.sh extension that asserts raw breadcrumb secrets never reach larch-logs/; regressions in streaming redaction or skip-and-continue would not fail CI
- **Proposed resolution**: Add a minimal in-scope test-larch-log.sh case for the breadcrumbs batch or state an explicit manual verification step in Testing strategy until item 4 lands

### FINDING_58:
- **Reviewer(s)**: Cursor-dyn-deferred-ci-gap
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/lint-foreground-markers.sh:64-82
- **Concern**: New scripts/breadcrumb-monitor.md and scripts/lib-redact-streaming.md are outside the linter scan set. Scenario: list_md_files only scans skills/** and .claude/rules — sibling docs under scripts/ are never scanned for stale Foreground required phrases or missing background+monitor pair examples
- **Proposed resolution**: Note in NEW sibling .md sections that fence examples must follow the background+monitor contract; defer expanding lint-foreground-markers scan to scripts/*.md to OUT_OF_SCOPE item 9

### OOS_1:
- **Description**: [OUT_OF_SCOPE] item 4 test harness scripts: scripts/test-breadcrumb-monitor.sh, scripts/test-breadcrumb-monitor-bash32.sh, scripts/test-redact-secrets.sh, scripts/test-larch-log.sh. Scenario: Core rollout has manual smoke coverage only, leaving monitor latency, truncation, symlink rejection, category enforcement, and committed-log redaction unguarded
- **Reviewer**: Codex-Arch
- **Severity**: latent
- **Focus area**: correctness
- **Location**: plan.txt:211
- **Phase**: design

### OOS_2:
- **Description**: [OUT_OF_SCOPE] item 7 Makefile/docs/agent-lint plumbing: Makefile, docs/linting.md, agent-lint.toml. Scenario: New harnesses and new script/docs siblings will not be discoverable or CI-enforced until target and allow-list plumbing lands
- **Reviewer**: Codex-Arch
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: plan.txt:213
- **Phase**: design

### OOS_3:
- **Description**: [OUT_OF_SCOPE] item 8 security and run-log docs: SECURITY.md, docs/run-logs.md. Scenario: Users and auditors will not have the durable policy description for raw tmpdir-only breadcrumb streams and mandatory streaming redaction before commit
- **Reviewer**: Codex-Arch
- **Severity**: latent
- **Focus area**: security
- **Location**: plan.txt:215
- **Phase**: design

### OOS_4:
- **Description**: [OUT_OF_SCOPE] item 9 expanded rewrite surface: .claude/skills/**/SKILL.md, .claude/rules/*.md. Scenario: Stale foreground-banner or foreground-comment patterns can continue to contradict the new background+monitor contract outside the core rollout
- **Reviewer**: Codex-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: plan.txt:217
- **Phase**: design

### OOS_5:
- **Description**: [OUT_OF_SCOPE] item 4 test harness coverage for monitor latency, done timing, redaction, path rejection, and larch-log breadcrumb redaction is deferred. Scenario: The core rollout can land without tests for the highest-risk contracts around streaming, traps, and fail-closed redaction
- **Reviewer**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-breadcrumb-monitor.sh:new; scripts/test-breadcrumb-monitor-bash32.sh:new; scripts/test-redact-secrets.sh:1-170; scripts/test-larch-log.sh:1-420
- **Phase**: design

### OOS_6:
- **Description**: [OUT_OF_SCOPE] item 7 Makefile, linting docs, and agent-lint allow-list plumbing is deferred. Scenario: New breadcrumb monitor tests/docs may be invisible to make lint or agent-lint until the deferred harness work lands
- **Reviewer**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: Makefile:4-79; docs/linting.md:220-280; agent-lint.toml:1-220
- **Phase**: design

### OOS_7:
- **Description**: [OUT_OF_SCOPE] item 8 security and run-log documentation for breadcrumb stream redaction is deferred. Scenario: Operators will not have durable docs for raw tmpdir streams, committed redaction, and residual sensitive-content risk
- **Reviewer**: Codex-Innovation
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md:1-178; docs/run-logs.md:1-70
- **Phase**: design

### OOS_8:
- **Description**: [OUT_OF_SCOPE] item 9 expanded stale foreground-banner rewrite is deferred. Scenario: Some skill/rule surfaces may still teach the old foreground-required pattern while the denylist moves to background plus breadcrumb-monitor
- **Reviewer**: Codex-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/lint-foreground-markers.sh:15-30; .claude/skills/*/SKILL.md; .claude/rules/*.md
- **Phase**: design

### OOS_9:
- **Description**: [OUT_OF_SCOPE] item 4 - breadcrumb monitor and streaming redactor harnesses deferred. Scenario: No dedicated harness will pin stream growth latency, partial-byte retention, truncation, DONE-sentinel timing, fail-closed redaction, symlink/path rejection, category enforcement, or committed-copy secret exclusion in this PR.
- **Reviewer**: Codex-Pragmatic
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/breadcrumb-monitor.sh:1-218; scripts/lib-redact-streaming.sh:1-42; scripts/test-redact-secrets.sh:1; scripts/test-larch-log.sh:1
- **Phase**: design

### OOS_10:
- **Description**: [OUT_OF_SCOPE] Item 4 test harness scripts are deferred. Scenario: Monitor latency, truncation, done-sentinel timing, symlink rejection, streaming PEM redaction, and committed-log secret exclusion remain without dedicated CI coverage in this core slice.
- **Reviewer**: Codex-Requirements
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/test-breadcrumb-monitor.sh:1; scripts/test-breadcrumb-monitor-bash32.sh:1; scripts/test-redact-secrets.sh:1; scripts/test-larch-log.sh:1
- **Phase**: design

### OOS_11:
- **Description**: Item 7 defers agent-lint.toml allow-list entries for test-breadcrumb-monitor* paths. Scenario: Follow-up item 4 adds Makefile-only harness scripts; without item 7 exclude entries agent-lint G004 will flag scripts/test-breadcrumb-monitor.sh and .md as dead until excluded (same pattern as scripts/test-lib-quiet.sh:661-664)
- **Reviewer**: Cursor-dyn-deferred-ci-gap
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: agent-lint.toml:282-1451; plan.txt:213-214
- **Phase**: design

### OOS_12:
- **Description**: Item 7 defers Makefile phony targets and test-harnesses-N shard registration. Scenario: make test-breadcrumb-monitor and make test-breadcrumb-monitor-bash32 are undefined today (verified: no Makefile match); issue acceptance requires them once follow-ups land
- **Reviewer**: Cursor-dyn-deferred-ci-gap
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: Makefile:4-60; plan.txt:213-214
- **Phase**: design

### OOS_13:
- **Description**: PR #2786 left breadcrumb-monitor.md missing; core plan adds it (item 5) — agent-lint on PR #2786 runtime files passes without item 7 exclusions. Scenario: pre-commit run agent-lint --all-files on current main exits 0; scripts/breadcrumb-monitor.sh is SKILL.md-reachable; scripts/lib-redact-streaming.sh is not separately excluded but does not fail CI today
- **Reviewer**: Cursor-dyn-deferred-ci-gap
- **Severity**: nit
- **Focus area**: correctness
- **Location**: scripts/breadcrumb-monitor.sh:3; plan.txt:145-168
- **Phase**: design
