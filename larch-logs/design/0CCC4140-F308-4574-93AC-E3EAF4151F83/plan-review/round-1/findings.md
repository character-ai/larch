### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-lib-quiet.sh:71-91
- **Concern**: Plan deletes emit_breadcrumb but leaves tests #4, #5, and #5b calling it. Scenario: After lib-quiet.sh drops the helpers, make lint / test-lib-quiet fails on undefined function
- **Proposed resolution**: Add these cases to the migration (switch helpers to larch_err / larch_errf and revise assertions) or delete/replace them in the same commit as the API removal

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-ci-wait.sh:255-305
- **Concern**: ci-wait.sh migration is listed; stream harness cases 5–7 are not. Scenario: Cases assert ndjson records from emit_breadcrumb_stderr; larch_errf writes stderr instead, so make lint / test-ci-wait fails
- **Proposed resolution**: Update test-ci-wait.sh (and test-ci-wait.md if needed) in the same PR—drop or rewrite stream cases to match quiet-log / stderr semantics, or defer ci-wait migration until Piece 3

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-larch-log.sh:224-275
- **Concern**: Plan removes the ndjson publish loop but does not update test-larch-log.sh. Scenario: Commit path still expects foo.ndjson from breadcrumbs/; quiet-only publish leaves tests failing despite “run test-larch-log.sh” in Testing strategy
- **Proposed resolution**: Extend Files to modify: adjust ndjson-centric commit assertions (e.g. lines 257–260) for quiet-log-only staging; keep redaction/hardlink cases that still apply

### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-apply-bump.sh:344-545
- **Concern**: Plan cites one assertion change; harness has many stdout breadcrumb checks. Scenario: apply-bump runs with LARCH_QUIET_DISABLE=1; emit_breadcrumb hits stdout but larch_err hits stderr, breaking retry/breadcrumb_shape cases
- **Proposed resolution**: List test-apply-bump.sh explicitly and move assertions to stderr.log (or merge streams in run_case) for all ^apply-bump: retry patterns

### FINDING_5:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-implement-bootstrap.sh:915-2623
- **Concern**: implement-bootstrap.sh is migrated; bootstrap harness is omitted. Scenario: Fifteen+ cases grep → step0: lines from captured stdout; larch_err under LARCH_QUIET_DISABLE=1 writes stderr, so test-implement-bootstrap fails
- **Proposed resolution**: Add skills/implement/scripts/test-implement-bootstrap.sh to Files to modify: capture stderr for breadcrumb assertions (tests using LARCH_QUIET_BREADCRUMB_FD=1 must follow the implement-bootstrap.md larch_err contract)

### FINDING_6:
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/breadcrumb-monitor.sh:141; scripts/lib-quiet.sh:147-152
- **Concern**: Plan removes larch_quiet_bc_valid_category while breadcrumb-monitor still calls it. Scenario: After the helper is removed, any monitored larch:bc line reaches larch_bm_emit_line and fails with command not found; make lint also runs test-breadcrumb-monitor
- **Proposed resolution**: Keep larch_quiet_bc_valid_category until Piece 3, or move the category validator into breadcrumb-monitor.sh in this PR

### FINDING_7:
- **Reviewer(s)**: Codex-Arch, Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-lib-quiet.sh:71-91
- **Concern**: Plan deletes only test cases #13-#18 but leaves earlier emit_breadcrumb tests. Scenario: With emit_breadcrumb removed, bash scripts/test-lib-quiet.sh fails at test #4 before reaching the retained lib-quiet coverage
- **Proposed resolution**: Delete or rewrite the #4/#5/#5b breadcrumb tests and update scripts/test-lib-quiet.md summary before renumbering the remaining cases

### FINDING_8:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-larch-log.sh:224-276; scripts/test-design-log-publish.sh:686-725
- **Concern**: Plan removes ndjson breadcrumb publishing but leaves harnesses that require ndjson breadcrumbs to publish. Scenario: Running the stated test-larch-log or test-design-log-publish paths still expects stream.ndjson/foo.ndjson in committed breadcrumbs and fails after the ndjson loop is removed
- **Proposed resolution**: Update the affected breadcrumb publish tests to assert quiet-log-only staging, and remove or retarget ndjson-only publish expectations

### FINDING_9:
- **Reviewer(s)**: Cursor-Edge, Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/breadcrumb-monitor.sh:141; scripts/lib-quiet.sh:147-152
- **Concern**: Plan removes larch_quiet_bc_valid_category but leaves breadcrumb-monitor.sh as Piece 3 scope. Scenario: Any Family B foreground monitor that processes a stream line will hit command not found under set -e and the wrapper reports monitor failure instead of the writer status
- **Proposed resolution**: Keep larch_quiet_bc_valid_category until breadcrumb-monitor.sh is migrated, or inline the category case statement in breadcrumb-monitor.sh in this PR

### FINDING_10:
- **Reviewer(s)**: Cursor-Edge, Codex-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/test-implement-bootstrap.sh:923-929; skills/review/scripts/test-review-core.sh:488-491; skills/review/scripts/test-dispatch-panel.sh:129-135; scripts/test-ship-pr.sh:1107-1156
- **Concern**: Plan converts breadcrumb output to larch_err but does not update adjacent stdout breadcrumb harnesses. Scenario: With LARCH_QUIET_DISABLE=1, larch_err writes stderr; these harnesses grep stdout-only captures, so make lint will fail after the mechanical callsite migration
- **Proposed resolution**: Update the listed tests and sibling docs to capture/assert stderr for migrated larch_err lines, or remove breadcrumb-specific stdout assertions where they no longer express the contract

### FINDING_11:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/breadcrumb-monitor.sh:141
- **Concern**: Plan removes larch_quiet_bc_valid_category from lib-quiet.sh but monitor still calls it. Scenario: Piece 3 defers monitor removal; after lib-quiet.sh drops the helper, sourcing monitor fails at runtime or drops all streamed lines
- **Proposed resolution**: Keep larch_quiet_bc_valid_category in lib-quiet.sh until Piece 3 removes breadcrumb-monitor.sh, or move the case statement into the monitor in the same PR

### FINDING_12:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/lib-quiet.sh:84-121, scripts/lib-larch-log.sh:464-478
- **Concern**: larch_err bypasses the quiet log that the plan makes the only committed breadcrumb source. Scenario: After migration a former emit_breadcrumb call writes to FD4/original stderr, not larch-quiet-*.log, so removing the ndjson loop silently drops durable breadcrumb content from larch-logs/*/breadcrumbs/
- **Proposed resolution**: Keep the ndjson path until writers target the quiet log, or use a minimal helper/path that writes intended breadcrumbs into the quiet log before making quiet logs the sole staging source

### FINDING_13:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-lib-quiet.sh:71-91, scripts/test-ci-wait.sh:255-305
- **Concern**: Test plan misses existing breadcrumb API and stream assertions outside deleted cases 13-18. Scenario: bash scripts/test-lib-quiet.sh still calls removed emit_breadcrumb in cases 4-5b, and scripts/test-ci-wait.sh still expects LARCH_BREADCRUMB_STREAM records after ci-wait.sh is converted to larch_errf
- **Proposed resolution**: Delete or retarget those tests in the same pass; for SIMPLE scope, remove breadcrumb API-specific cases and update ci-wait assertions to the proposed stderr/quiet-log behavior

### FINDING_14:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: latent
- **Focus area**: security
- **Location**: SECURITY.md:28-32, SECURITY.md:275-318, docs/run-logs.md:96-113
- **Concern**: Plan changes breadcrumb publication semantics but leaves canonical security and run-log docs stale. Scenario: After ndjson publication is removed, docs still describe regular *.ndjson stream publication and its security boundary, which gives operators the wrong durable-log contract
- **Proposed resolution**: Update only the affected breadcrumb publication paragraphs to say quiet-log-only staging and remove obsolete ndjson fallback/security claims

### FINDING_15:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lib-quiet.md:20-27; scripts/implement-bootstrap.sh:163-187; scripts/ship-pr.sh; scripts/ci-wait.sh:184-284
- **Concern**: Plan maps every emit_breadcrumb/emit_breadcrumb_stderr callsite to larch_err/larch_errf only. Scenario: With LARCH_QUIET_BREADCRUMBS=1 progress text must surface on caller stdout/FD3 (and with LARCH_BREADCRUMB_STREAM set stream-only NDJSON feeds breadcrumb-monitor); larch_err/larch_errf always route to stderr/FD4 and never write larch:bc records — live /implement progress and monitor streaming regress until Piece 3
- **Proposed resolution**: Do not apply blind rename: keep a minimal stdout/stream helper for gated callsites until Piece 3, or explicitly drop both contracts and in the same PR retarget skills/implement/SKILL.md consumer expectations plus harnesses that grep stdout (test-ship-pr.sh:1107-1156, skills/implement/scripts/test-implement-bootstrap.sh:2489-2623)

### FINDING_16:
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/breadcrumb-monitor.sh:137-141
- **Concern**: Plan removes larch_quiet_bc_valid_category from lib-quiet.sh while breadcrumb-monitor.sh still calls it and the plan says breadcrumb-monitor.sh stays in Piece 3 scope. Scenario: After lib-quiet.sh drops the helper, monitor processing of larch:bc stream lines emits command-not-found noise and drops valid progress lines; scripts/test-breadcrumb-monitor.sh cases for valid categories and partial lines would fail
- **Proposed resolution**: Update the plan to either keep larch_quiet_bc_valid_category until breadcrumb-monitor.sh is retired or move the validator into breadcrumb-monitor.sh before removing the lib helper, and include bash scripts/test-breadcrumb-monitor.sh in validation

### FINDING_17:
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ci-wait.sh:184,270
- **Concern**: The plan adds newlines to the two no-newline emit_breadcrumb_stderr callsites while claiming this preserves current visual behavior. Scenario: emit_breadcrumb_stderr currently preserves larch_errf printf semantics with no implicit newline, so CI waiting and dot progress stay on one line; adding \n changes operator output to one line per dot
- **Proposed resolution**: Convert those two callsites to larch_errf without adding newlines: larch_errf "⏳ CI: waiting" and larch_errf "."

### FINDING_18:
- **Reviewer(s)**: Cursor-dyn-callsite-census, Codex-dyn-callsite-census
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-lib-quiet.sh:71-91
- **Concern**: Plan leaves three generated-helper emit_breadcrumb callsites outside deleted cases 13-18; actual census is 7 emit_breadcrumb plus 2 emit_breadcrumb_stderr callsites in this file, not only the 4 plus 2 covered by lines 141-196.. Scenario: After scripts/lib-quiet.sh removes emit_breadcrumb, bash scripts/test-lib-quiet.sh still executes helpers from cases 4, 5, and 5b and fails with emit_breadcrumb: command not found.
- **Proposed resolution**: Update or delete the breadcrumb quiet/visible/alternate-fd tests at lines 71-91 in the same minimal pass, and sync scripts/test-lib-quiet.md if those contracts are removed.

### FINDING_19:
- **Reviewer(s)**: Cursor-dyn-callsite-census, Codex-dyn-callsite-census
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ci-wait.sh:184-270
- **Concern**: Plan adds newlines to the two emit_breadcrumb_stderr callsites that currently omit them, but larch_errf has printf semantics and no implicit newline, so this changes behavior rather than preserving it.. Scenario: CI wait output changes from an inline waiting banner plus dot progress to one line per banner/dot, making the operator progress display noisier and unlike the current script.
- **Proposed resolution**: Convert line 184 to larch_errf "⏳ CI: waiting" and line 270 to larch_errf "." with no added newline; keep the existing newline-bearing formats unchanged.

### FINDING_20:
- **Reviewer(s)**: Cursor-dyn-substitution-fidelity, Codex-dyn-substitution-fidelity
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ci-wait.sh:184-191,270-273
- **Concern**: Adding newline escapes to the two no-newline progress formats is not substitution-fidelity. Scenario: `emit_breadcrumb_stderr` currently falls through to `larch_errf` with no implicit newline when no stream (scripts/lib-quiet.sh:345-376). The line 184 banner and line 270 dots intentionally share a line; later warning/status formats already start with `\n`, and line 249-250 emits the final separator. Adding `\n` prints every dot on its own line and creates an extra blank before the every-sixth-poll status.
- **Proposed resolution**: Convert those two calls to `larch_errf "⏳ CI: waiting"` and `larch_errf "."` without adding `\n`; keep the existing leading-newline formats unchanged.

### FINDING_21:
- **Reviewer(s)**: Cursor-dyn-substitution-fidelity, Codex-dyn-substitution-fidelity
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-lib-quiet.sh:71-91
- **Concern**: Plan removes `emit_breadcrumb` but leaves earlier lib-quiet tests that still invoke it. Scenario: The plan deletes test cases #13-#18 only, but tests #4, #5, and #5b build helper scripts that call `emit_breadcrumb`. After `scripts/lib-quiet.sh` drops that function, `bash scripts/test-lib-quiet.sh` fails with command-not-found before reaching the retained paired-PID and larch_err coverage.
- **Proposed resolution**: Delete or rewrite the breadcrumb quiet/surfacing tests at lines 71-91, and update `scripts/test-lib-quiet.md` to remove the remaining `emit_breadcrumb` public-contract references.

### FINDING_22:
- **Reviewer(s)**: Cursor-dyn-substitution-fidelity, Codex-dyn-substitution-fidelity
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/collect-agent-results.sh:156-171; scripts/lib-voter-parse-rate.sh:256; scripts/lib-quiet.sh:84-121
- **Concern**: Dropping callsite `>&2` while switching to `larch_err` changes the descriptor target in initialized quiet sessions. Scenario: `larch_quiet_init` saves original stderr on FD4, then redirects FD2 to the quiet log. Current `emit_breadcrumb ... >&2` writes to current FD2 when breadcrumbs are not surfaced, so normal initialized `collect-agent-results.sh` logs these retry messages. Proposed `larch_err` writes to FD4, making them operator-visible. That may be desired, but it is not a no-op substitution.
- **Proposed resolution**: If visible stderr is intended, say so in the plan and adjust tests/docs around the visibility change. If strict destination preservation is required, replace these with `printf '%s\n' ... >&2` instead of `larch_err`.

### FINDING_23:
- **Reviewer(s)**: Cursor-dyn-piece-boundary, Codex-dyn-piece-boundary
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/breadcrumb-monitor.sh:133-142; scripts/lib-quiet.sh:147-152
- **Concern**: The plan removes larch_quiet_bc_valid_category even though breadcrumb-monitor.sh still calls it in its larch:bc line validation path.. Scenario: breadcrumb-monitor.sh is explicitly deferred to Piece 3, so after lib-quiet.sh drops the helper, any monitor run that reads a breadcrumb line hits command not found under set -e and exits instead of surfacing progress.
- **Proposed resolution**: Keep larch_quiet_bc_valid_category until Piece 3 removes or rewrites breadcrumb-monitor.sh, or inline the same category case check in breadcrumb-monitor.sh as part of this plan.
