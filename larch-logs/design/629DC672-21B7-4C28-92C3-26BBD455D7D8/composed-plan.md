## Plan

# Implementation Plan: Finish breadcrumb propagation rollout (issue #2790)

## Context — already complete

The following items from the issue body are already done per pre-design audit:

- **Item 1** (done-trap wiring for 9 denylisted scripts): all of `scripts/ship-pr.sh`, `scripts/ci-wait.sh`, `scripts/collect-agent-results.sh`, `scripts/dispatch-plan-voters.sh`, `scripts/dispatch-with-waterfall.sh`, `scripts/run-step5-review.sh`, `skills/implement/scripts/run-step2-dispatch.sh`, `skills/implement/scripts/step2-implement.sh`, and `skills/review-and-fix/scripts/review-and-fix.sh` already call `larch_quiet_append_done_trap` after their final EXIT trap. Wrapper scripts source `lib-quiet.sh` and call `larch_quiet_init` at the top. No code changes needed.
- **Item 9** (expanded foreground-banner rewrites in `.claude/skills/**/SKILL.md` and `.claude/rules/*.md`): `scripts/lint-foreground-markers.sh` runs clean against `.claude/`; the literal "Foreground required" pattern does not occur anywhere under `.claude/`. No code changes needed.

Acceptance still requires these to pass on CI, but no new edits land for items 1 or 9.

## Approach

The remaining work spans three contract surfaces — runtime completion coupling (already done), streamed user-visible progress (`emit_breadcrumb --category=`), and durable redacted logs (committed `breadcrumbs/`) — plus the doc/test/plumbing tail. Plan review surfaced seven load-bearing corrections; all are folded in:

1. **Breadcrumb source bridging.** Runtime streams live in the session tmpdir (`$IMPLEMENT_TMPDIR/breadcrumbs/`, `$DESIGN_TMPDIR/breadcrumbs/`, `$REVIEW_TMPDIR/breadcrumbs/`, `$RESEARCH_TMPDIR/breadcrumbs/`), NOT under `larch_log_run_dir`. `scripts/larch-log.sh` must explicitly derive the session-tmpdir source for the commit step. Publish callers (`scripts/refresh-run-logs.sh`, `scripts/design-log-publish.sh`, `scripts/implement-finalize.sh` Step 7a/flush path) must invoke that source explicitly so committed `larch-logs/<run-id>/breadcrumbs/` actually contains the live streams.
2. **Fail-closed redaction with no raw copy.** The existing `cp -rp "$src_path/." "$repo_path/"` must NOT touch raw breadcrumbs. Stage the redacted output in a temp directory, then atomically `mv` only after every per-file redactor invocation exits 0. Redactor failure leaves no `larch-logs/<run-id>/breadcrumbs/` directory and no raw files staged.
3. **Two-stage redaction.** Commit pipeline: `redact-tmpdir-paths.sh | redact-secrets.sh --streaming --state-file <tmp>`. Fail-closed at either stage.
4. **ci-wait stderr-preserving helper.** Add `emit_breadcrumb_stderr` to `scripts/lib-quiet.sh` that mirrors `larch_errf`'s no-newline `>&4` semantics: when `LARCH_BREADCRUMB_STREAM` is set, it emits the structured breadcrumb record (with `--category=`); when the stream is unset, it falls back to `larch_errf`-style stderr (preserving printf format strings, including the no-newline dot progress). Use this helper for all `ci-wait.sh` progress migrations so the existing stderr byte-for-byte contract is preserved.
5. **RESEARCH_TMPDIR path-scope.** Extend `larch_bm_under_session_tmp()` in `scripts/breadcrumb-monitor.sh` to also accept `$RESEARCH_TMPDIR/*`. Update path-scope tests and `scripts/breadcrumb-monitor.md`.
6. **Stream-relevant callsite scope (expanded).** Add to the migration set: `skills/review-and-fix/scripts/review-implement-step5-loop.sh` (3 callsites), `scripts/lib-voter-parse-rate.sh` (1 callsite under `dispatch-plan-voters.sh`'s inherited stream), and `scripts/implement-finalize.sh` (any uncategorized `emit_breadcrumb` calls reachable from `ship-pr.sh`'s inherited stream). Final stream-relevant inventory: `scripts/ship-pr.sh` (23), `skills/review-and-fix/scripts/review-and-fix.sh` (20), `skills/review-and-fix/scripts/review-implement-step5-loop.sh` (3), `skills/review/scripts/review-core.sh` (4), `scripts/collect-agent-results.sh` (2), `skills/review/scripts/dispatch-panel.sh` (1), `scripts/lib-voter-parse-rate.sh` (1), `scripts/implement-finalize.sh` (TBD — audited and migrated). Total: ~54 callsites.
7. **Commit-only breadcrumbs (not a batch-table row).** `scripts/larch-log-batches.sh` registry has a fixed 4-field schema for single-file batches with extension/mode/sanitizer; a directory + sanitizer-command-with-args batch row cannot fit without breaking the parser and `scripts/test-larch-logs-batches.sh`. Treat breadcrumbs as a separate **commit-only artifact class** in `scripts/larch-log.sh` — no entry in the batch registry. Document the artifact class in `scripts/larch-log.md` and `scripts/larch-log-batches.md`.

The migration lands as one bundled PR in this order: lib-quiet helper + path-scope extension first (foundational), then ci-wait migration (uses new helper), then stream-relevant category migration on all ~54 callsites, then larch-log commit-time breadcrumbs handling (with publish-caller wiring), then test harness expansion + new bash32 sibling + test-redact-secrets / test-larch-log extensions, then sibling .md files, then docs (SECURITY/run-logs/linting), then Makefile + agent-lint.toml plumbing.

Category routing for emit_breadcrumb migrations uses the fixed vocabulary enforced by `larch_quiet_bc_valid_category()` in `scripts/lib-quiet.sh`: `{progress, warn, stall, retry, escalate, wait-ci, network-flake}`. Per-script routing rule: lines starting with `→` → `progress`; lines starting with `⚠`/`❌` → `warn`; `⛔ ... stalled` → `stall`; CI-wait progress → `wait-ci`; transient-network/retry → `retry`/`network-flake` (use `network-flake` only when the message text explicitly names a network flake); rebase/escalation handoff messages → `escalate`.

## Files to modify/create

### UPDATED: `scripts/lib-quiet.sh`

Add `emit_breadcrumb_stderr` helper that mirrors `larch_errf`'s no-newline `>&4` semantics with `printf`-style format support:

- Signature: `emit_breadcrumb_stderr --category=NAME FORMAT [ARGS...]`
- When `LARCH_BREADCRUMB_STREAM` is set: emit a structured `larch:bc t=... c=NAME text=...` record to the stream (text is the formatted output of `printf FORMAT ARGS...`, newlines collapsed to spaces).
- When `LARCH_BREADCRUMB_STREAM` is unset: fall back to `larch_errf FORMAT ARGS...` so the existing no-newline dot-progress contract is preserved on stderr.
- The helper does NOT print to stdout / quiet log on the stream-unset path (matching `larch_errf` semantics).

The existing `emit_breadcrumb` function is unchanged. The new helper is purely additive.

### UPDATED: `scripts/breadcrumb-monitor.sh`

Extend `larch_bm_under_session_tmp()` to also accept `$RESEARCH_TMPDIR/*`. The function becomes:

```sh
larch_bm_under_session_tmp() {
    local p=$1
    case "$p" in
        "${IMPLEMENT_TMPDIR:-}"/*|"${DESIGN_TMPDIR:-}"/*|"${REVIEW_TMPDIR:-}"/*|"${RESEARCH_TMPDIR:-}"/*) return 0 ;;
        *) return 1 ;;
    esac
}
```

### UPDATED: `scripts/breadcrumb-monitor.md`

Update the path-scope section to list all four allowed roots (IMPLEMENT/DESIGN/REVIEW/RESEARCH).

### UPDATED: `scripts/ci-wait.sh`

Convert the 13 `larch_errf` progress callsites at lines 184, 268, 271, 251, 253, 282, 257 to use `emit_breadcrumb_stderr --category=wait-ci`. Lines 191, 207, 222, 238, 255 (warnings/bails/timeouts/decide-failure) remain on `larch_err` — these are genuine error/warning paths. Line 249 (terminating newline) remains on `larch_errf`.

The new `emit_breadcrumb_stderr` helper guarantees byte-for-byte stderr compatibility when `LARCH_BREADCRUMB_STREAM` is unset (the dot progress at line 268 stays no-newline; per-poll updates at line 271 keep their newline). When the stream IS set, structured `c=wait-ci` records flow to the breadcrumb stream and the legacy stderr text is suppressed (handled inside the helper).

### UPDATED: `scripts/ci-wait.md`

Document the progress-tier helper migration (emit_breadcrumb_stderr) and the stream-set vs stream-unset contract for `ci-wait`'s stderr output.

### UPDATED: `scripts/ship-pr.sh`

Migrate 23 `emit_breadcrumb` callsites to add `--category=` per the per-script emoji-prefix routing rule in the Approach section.

### UPDATED: `scripts/ship-pr.md`

Document the breadcrumb category vocabulary used by ship-pr and the inherited-stream contract for any sourced/child scripts.

### UPDATED: `skills/review-and-fix/scripts/review-and-fix.sh`

Migrate 20 `emit_breadcrumb` callsites to add `--category=` per the same emoji-prefix routing.

### UPDATED: `skills/review-and-fix/scripts/review-implement-step5-loop.sh`

Migrate 3 `emit_breadcrumb` callsites at lines 103, 117, 296. These run under `run-step5-review.sh`'s inherited stream. Routing per emoji prefix.

### UPDATED: `skills/review/scripts/review-core.sh`

Migrate 4 `emit_breadcrumb` callsites: 3 `⚠ review-core: ...` → `--category=warn`; 1 `→ review: consolidating findings` → `--category=progress`.

### UPDATED: `scripts/collect-agent-results.sh`

Migrate 2 `emit_breadcrumb` callsites per the emoji-prefix routing.

### UPDATED: `skills/review/scripts/dispatch-panel.sh`

Migrate the 1 `emit_breadcrumb "→ review: launching ..."` callsite to `--category=progress`.

### UPDATED: `scripts/lib-voter-parse-rate.sh`

Migrate the 1 retry-preserved `emit_breadcrumb` callsite (around line 262-272) to `--category=retry`. This runs under `dispatch-plan-voters.sh`'s inherited stream in the design plan-review flow.

### UPDATED: `scripts/implement-finalize.sh`

Two changes in this file:

1. **Category migration**: audit `emit_breadcrumb` callsites; migrate any that run under `ship-pr.sh`'s inherited stream to add `--category=` per emoji-prefix routing. Specific lines determined during implementation by running `grep -n 'emit_breadcrumb' scripts/implement-finalize.sh` and verifying which run under a stream-set path (call chain reachable from a `ship-pr.sh` invocation).
2. **Breadcrumbs commit step (Step 7a / flush)**: add an invocation of the new breadcrumbs commit step at the Step 7a / flush path before the final commit. Use `$IMPLEMENT_TMPDIR/breadcrumbs/` as the source.

### UPDATED: `scripts/larch-log.sh`

Add a new commit-time step that handles breadcrumbs as a **commit-only artifact class** (not a batch-table row):

1. **Source resolution**: derive the session-tmpdir source from the `--log-root` argument or explicit env (e.g., `IMPLEMENT_TMPDIR=$(dirname "$LARCH_LOG_ROOT")` when log root is `$IMPLEMENT_TMPDIR/larch-logs`). Validate the path exists; if absent, log a warning and skip (empty breadcrumbs/ is valid).
2. **Exclude from broad copy**: explicitly skip `breadcrumbs/` in the existing `cp -rp "$src_path/." "$repo_path/"` so raw breadcrumbs never enter the repo worktree.
3. **Stage redacted output in a temp directory**: allocate `<tmpdir>/breadcrumbs-staging.<pid>/`. For each regular file in the session-tmpdir breadcrumbs directory:
   a. Allocate per-file `--state-file` paths under the temp directory.
   b. Run: `redact-tmpdir-paths.sh < <input> | redact-secrets.sh --streaming --state-file <state> > <staging>/<basename>`.
   c. If EITHER stage exits non-zero, fail closed: abort the commit, delete the staging directory, leave no `larch-logs/<run-id>/breadcrumbs/`, and exit with a clear error naming the file and the failing stage.
4. **Atomic publish**: only after every file redacts successfully, `mv <staging>` → `<repo_path>/breadcrumbs` (atomic directory move). Reject symlinks at the source path-scope check.
5. **Empty source**: if the session breadcrumbs directory is empty or absent, skip publication entirely (do not create an empty `breadcrumbs/` in the committed run log).

Bash 3.2-portable iteration: `for f in "$source_dir"/*; do [ -e "$f" ] || continue; ...; done`.

### UPDATED: `scripts/larch-log.md`

Document:
- The new commit-only breadcrumbs artifact class (separate from the batch table).
- Source-tmpdir resolution rules and the explicit publish-caller contract.
- The two-stage redaction pipeline (`redact-tmpdir-paths.sh | redact-secrets.sh --streaming --state-file`).
- Fail-closed atomic publish semantics.
- Empty-source skip behavior.

### UPDATED: `scripts/larch-log-batches.sh`

No code change — breadcrumbs is NOT added as a batch-table row. The 4-field schema cannot represent a directory with a multi-arg sanitizer command. This file remains for the existing single-file batches; breadcrumbs is handled exclusively in `scripts/larch-log.sh`'s commit path.

### UPDATED: `scripts/larch-log-batches.md`

Document why breadcrumbs is a commit-only artifact class and is NOT in the batch table (link to `scripts/larch-log.md`).

### UPDATED: `scripts/refresh-run-logs.sh`

Add an explicit invocation of the breadcrumbs commit step in the refresh path (calls into `scripts/larch-log.sh` commit with the session-tmpdir source derived from the run context). Document the caller contract.

### UPDATED: `scripts/design-log-publish.sh`

Add the breadcrumbs commit step at the appropriate publish boundary (just before the final `git add` / commit). Use the session-tmpdir-resolved source for `$DESIGN_TMPDIR/breadcrumbs/`.

### UPDATED: `scripts/test-breadcrumb-monitor.sh`

Extend the existing 6-test harness to add coverage for:

- **Stream growth latency**: assert the monitor surfaces a breadcrumb line on stdout within `<poll-interval + 1s>` of being written to the stream.
- **Partial-byte retention**: write a chunk ending mid-line; assert the monitor does NOT emit the partial line; finish the line; assert the line is emitted.
- **Truncation/rotation**: shrink the stream after partial reads; assert `WARN reset` and resume.
- **Failure-tail surfacing with PEM redaction intact**: write a PEM block into the stream, then non-zero `EXIT_CODE` to the done sentinel; assert failure tail emitted, PEM redacted.
- **Redactor non-zero exit fail-closed**: stub `lib-redact-streaming.sh` to exit non-zero on a specific line; assert `WARN redact-drop-line` emitted and raw content not printed.
- **Path-scope rejection**: pass `--stream` outside the allowed roots; assert exit 2.
- **Path-scope acceptance for RESEARCH_TMPDIR**: pass `--stream` under `$RESEARCH_TMPDIR/`; assert acceptance (positive test for the new path-scope extension).
- **Symlink rejection**: assert exit 2.
- **Category enforcement**: write a `larch:bc ... c=invalid text=...` line; assert dropped from emission.

### UPDATED: `scripts/test-breadcrumb-monitor.md`

Document the expanded coverage list.

### NEW: `scripts/test-breadcrumb-monitor-bash32.sh`

Sibling harness that re-runs `scripts/test-breadcrumb-monitor.sh` test body under `/bin/bash` (macOS Bash 3.2):

1. Probe `/bin/bash --version`; if missing or reports Bash 4+, emit `SKIP=no-bash32` and exit 0.
2. Otherwise invoke `/bin/bash scripts/test-breadcrumb-monitor.sh` (or source the body under `/bin/bash`).
3. Assert byte-for-byte parity.

Bash 3.2-clean per `BASH_AUTHORING.md` §3.

### NEW: `scripts/test-breadcrumb-monitor-bash32.md`

Sibling doc per `.claude/rules/script-md-siblings.md`: argv, env-var interactions, skip semantics (`SKIP=no-bash32`), exit codes, dependency portability requirements.

### UPDATED: `scripts/test-redact-secrets.sh`

Add three streaming-mode PEM cases:

- **Complete PEM block**: redact in one invocation; assert placeholder.
- **Split-across-inputs via `--state-file`**: first invocation receives BEGIN + partial body; second invocation reuses the same `--state-file` for the remainder; assert combined output is fully redacted.
- **Tail starting mid-PEM**: standalone END line with a fresh `--state-file`; assert no false-positive corruption.

### UPDATED: `scripts/test-redact-secrets.md`

Document the new streaming-mode coverage.

### UPDATED: `scripts/test-larch-log.sh`

Add three tests:

1. **Breadcrumbs PEM redaction in committed copy**: set up a synthetic session-tmpdir `breadcrumbs/foo.ndjson` containing a known PEM; run `larch-log.sh` commit; assert the committed `larch-logs/<run-id>/breadcrumbs/foo.ndjson` contains the redacted placeholder and NO raw PEM.
2. **Breadcrumbs tmpdir-path redaction in committed copy**: include `$IMPLEMENT_TMPDIR`-style paths in the synthetic breadcrumb file; assert they are rewritten to `<IMPLEMENT_TMPDIR>` / scrubber-defined placeholders in the committed copy.
3. **Fail-closed on redactor failure**: place a synthetic breadcrumb file containing a marker that causes `redact-secrets.sh --streaming` to exit non-zero; run the commit; assert non-zero exit, no `larch-logs/<run-id>/breadcrumbs/` directory, no raw files staged in the repo worktree.

### UPDATED: `scripts/test-larch-log.md`

Document the new breadcrumb-pipeline assertions.

### UPDATED: `scripts/test-larch-logs-batches.sh`

Audit invariants asserted by this harness. Since breadcrumbs is NOT added to the batch table, no expected-batch-list update is needed — but assert explicitly that `breadcrumbs/` does NOT appear as a batch entry (negative assertion documenting the commit-only artifact class).

### NEW: `scripts/lib-redact-streaming.md`

Sibling .md per `.claude/rules/script-md-siblings.md`:

- **Purpose**: line-oriented wrapper around `redact-secrets.sh --streaming` with persistent PEM state.
- **Argv**: `--state-file PATH` (required), `-h` / `--help`.
- **Env-var interactions**: none beyond inherited `redact-secrets.sh`.
- **Mode-selection logic**: every input line redacted; PEM state persists across calls in `--state-file`.
- **Exit codes**: 0 success; 2 unknown option; propagates redact-secrets.sh exit on failure.
- **Redaction failure semantics**: caller (e.g., `breadcrumb-monitor.sh`, `larch-log.sh`) treats non-zero exit as fail-closed.
- **Foreground-duplication guard interaction**: cite the surfaced-sentinel mechanism in `breadcrumb-monitor.sh`.

### UPDATED: `SECURITY.md`

Add a "Breadcrumb stream redaction" subsection:

- Raw breadcrumb streams are tmpdir-only — never committed in raw form.
- The foreground `breadcrumb-monitor.sh` consumer applies `lib-redact-streaming.sh` to every emitted line; redactor failure is fail-closed (`WARN redact-drop-line` emitted, line dropped).
- Committing breadcrumbs to `larch-logs/<run-id>/breadcrumbs/` runs through the two-stage pipeline `redact-tmpdir-paths.sh | redact-secrets.sh --streaming --state-file <tmp>`; failure at either stage aborts the commit with no `larch-logs/<run-id>/breadcrumbs/` directory created and no raw files staged.
- Residual sensitive-content risk: the redactors cover PEM blocks, known secret token shapes, and tmpdir/operator-repo paths; internal URLs, private hostnames, and PII are not scrubbed and require operator discipline.

### UPDATED: `docs/run-logs.md`

Document:
- The per-run `$<SESSION>_TMPDIR/breadcrumbs/` directory (where `<SESSION>` is `IMPLEMENT` / `DESIGN` / `REVIEW` / `RESEARCH`) as the source for committed breadcrumbs.
- Commit contract: `scripts/larch-log.sh` resolves the session-tmpdir source explicitly from the publish caller; pipes each file through `redact-tmpdir-paths.sh | redact-secrets.sh --streaming --state-file <tmp>` into a staging directory; atomically `mv` to `larch-logs/<run-id>/breadcrumbs/` only after every file redacts successfully. Fail-closed on either stage; no partial publish.
- Empty or absent source directory results in no `breadcrumbs/` in the committed run log (skip, not error).

### UPDATED: `docs/linting.md`

Add target rows for `test-breadcrumb-monitor` and `test-breadcrumb-monitor-bash32` under the existing harness-table section.

### UPDATED: `Makefile`

Add `.PHONY: test-breadcrumb-monitor-bash32` (`test-breadcrumb-monitor` is already declared). Add a recipe:

```make
test-breadcrumb-monitor-bash32:
	bash scripts/harness-timer.sh $@ bash scripts/test-breadcrumb-monitor-bash32.sh
```

Register `test-breadcrumb-monitor-bash32` in shard `test-harnesses-18` (co-locates with `test-breadcrumb-monitor`).

### UPDATED: `agent-lint.toml`

Add allow-list entries for:

- `scripts/test-breadcrumb-monitor-bash32.sh`
- `scripts/test-breadcrumb-monitor-bash32.md`
- `scripts/lib-redact-streaming.md`

Use the same comment-block style as the existing `scripts/test-breadcrumb-monitor.sh` / `.md` entries (explain that the bash32 harness covers the same monitor under macOS Bash 3.2 and lives in `test-harnesses-18`).

## Edge cases

- **Empty session-tmpdir `breadcrumbs/` directory**: a run may finish without any backgrounded denylisted scripts firing. `scripts/larch-log.sh` treats empty or missing source as no-op (no `breadcrumbs/` in committed run log; no error).
- **Partial-line tail**: a backgrounded script crashing mid-write may leave a partial last line. The monitor buffers and flushes residual content after the done sentinel; the larch-log commit redactor reads stdin until EOF (partial lines pass through).
- **Per-file `--state-file` isolation**: every committed breadcrumb file gets its own state file under the larch-log temp directory; PEM state cannot leak across files. State files are deleted after the commit completes.
- **Symlink rejection at commit source**: the larch-log commit walker applies the same `breadcrumb-monitor.sh` symlink-rejection check; if a symlink appears in the source breadcrumbs directory, the commit aborts.
- **Category mismapping ambiguity**: when an `emit_breadcrumb` line carries no emoji or prefix convention (e.g., legacy free-form text in `review-and-fix`), default to `--category=progress`. Reviewers should spot-check the diff for any non-progress lines that should have been `warn`/`retry`.
- **Bash 3.2 absent on Linux CI**: the bash32 harness probes `/bin/bash --version` and emits `SKIP=no-bash32` when not Bash 3.2.
- **`emit_breadcrumb_stderr` stream-set path**: when the stream is set, the helper formats with `printf FORMAT ARGS`, collapses newlines to spaces, and emits a single `larch:bc` record. Multi-line format strings (rare in `ci-wait.sh`) become single-line breadcrumb records — acceptable since structured records do not preserve multi-line layout.
- **RESEARCH_TMPDIR allowance interaction with existing tests**: the path-scope tests in `test-breadcrumb-monitor.sh` previously only covered IMPLEMENT/DESIGN/REVIEW; adding a RESEARCH_TMPDIR positive test does not regress existing rejection assertions for unrelated paths.

## Failure modes

1. **Empty committed `breadcrumbs/` due to source mis-resolution.** Earliest signal: a run log with non-empty `$<SESSION>_TMPDIR/breadcrumbs/` but absent or empty `larch-logs/<run-id>/breadcrumbs/`. Mitigation: explicit publish-caller wiring in `refresh-run-logs.sh` / `design-log-publish.sh` / `implement-finalize.sh` named in this plan; smoke test in `test-larch-log.sh` asserts the source-to-destination bridge with a real `$IMPLEMENT_TMPDIR/breadcrumbs/` layout.
2. **Raw secret on disk after redactor failure.** Earliest signal: a `larch-logs/<run-id>/breadcrumbs/` containing partial / unredacted PEMs after a commit that reported failure. Mitigation: staging-directory + atomic-mv pattern named in `scripts/larch-log.sh` UPDATED section; the `test-larch-log.sh` fail-closed test asserts no partial directory survives.
3. **Wrong category mapping silently drops breadcrumbs.** Earliest signal: `WARN unknown-category=<missing>` in stderr or absence of expected progress in the breadcrumb stream. Mitigation: the per-script emoji-prefix routing table is mechanical; tests under `test-ci-wait.sh` (and similar) assert `c=wait-ci` records reach the monitor when the stream is set.

## Testing strategy

- Run `make test-breadcrumb-monitor`, `make test-breadcrumb-monitor-bash32`, `make test-redact-secrets`, `make test-larch-log`, `make test-ci-wait`, `make test-ship-pr`, `make test-review-and-fix`, `make test-collect-agent-results`, `make test-lib-quiet`, `make test-larch-logs-batches` after the implementation lands.
- Run `make lint`, `make lint-foreground-markers`, `make lint-bash32` to verify no regressions in static-scan tooling.
- Run `make test-lib-quiet` to verify category vocabulary enforcement remains intact and `emit_breadcrumb_stderr` behavior is asserted in both stream-set and stream-unset paths.
- Manual smoke (per issue body acceptance): execute `/implement` on a tiny issue end-to-end and visually verify streaming breadcrumbs render in chat during a backgrounded `collect-agent-results.sh`, `ship-pr.sh`, and `ci-wait.sh` invocation; also verify committed `larch-logs/<run-id>/breadcrumbs/` is non-empty when the run produced streams.
- Regression: byte-for-byte stdout/stderr comparison for `ci-wait.sh` against current baseline when `LARCH_BREADCRUMB_STREAM` is unset (existing `test-ci-wait.sh` already pins this; the new `emit_breadcrumb_stderr` helper must preserve byte-identical output on this path). Add an `LARCH_BREADCRUMB_STREAM`-set variant asserting `c=wait-ci` records appear in the stream while stderr stays empty (or only carries genuine errors via `larch_err`).

## Acceptance

- `make lint`, `make lint-foreground-markers`, `make lint-bash32`, `make test-lib-quiet`, `make test-breadcrumb-monitor`, `make test-breadcrumb-monitor-bash32`, `make test-redact-secrets`, `make test-lint-foreground-markers`, `make test-larch-log`, `make test-larch-logs-batches`, `make test-ci-wait`, `make test-ship-pr`, `make test-review-and-fix`, `make test-collect-agent-results`, the rewritten Step 5 anti-polling harness, agent-lint, and the halt-rate regression harness all pass on CI before merge.
- After this issue lands, no callsite of the 9 denylisted scripts ships in `skills/**/SKILL.md` / references without a paired `breadcrumb-monitor.sh` consumer.
- All stream-relevant `emit_breadcrumb` callers (the ~54 callsites enumerated in the plan) pass an explicit `--category=` argument matching the fixed vocabulary.
- Manual smoke: run `/implement` on a tiny issue end-to-end and verify (a) the user sees streaming breadcrumbs in chat during a backgrounded `collect-agent-results.sh` / `ship-pr.sh` / `ci-wait.sh`, AND (b) the committed `larch-logs/<run-id>/breadcrumbs/` directory is non-empty and contains the redacted streams.
- The follow-up OOS issue #2833 (RESEARCH_TMPDIR path-scope) is addressed as part of the in-scope work in this plan (FINDING_6/17/25/31), so it closes on the same PR landing.

diff_lines: 750
