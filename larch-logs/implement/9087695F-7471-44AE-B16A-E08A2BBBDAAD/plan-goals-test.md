## Goal
Replace the foreground-required contract for 9 denylisted Family-B scripts with a paired background+breadcrumb-monitor pattern that propagates breadcrumbs from long-running helper scripts back to chat, enforced by repurposed AND-semantics lint.

## Implementation Plan
## Plan

# Implementation Plan: breadcrumb propagation from background helper scripts to main chat

Implements user-resolved scope from Round 1 (see `discussion-round1.md`) and dialectic resolutions (see `dialectic-resolutions.md` — DECISION_1: Monitor with Bash-fallback for chat-bound display; DECISION_2: explicit skill-level pairing enforced by repurposed lint). All 24 Step 3 accepted findings are reflected in the contracts below.

## Approach

The Claude Code harness sometimes backgrounds Bash tool calls that were authored as foreground; when that happens, the script's FD-3 breadcrumbs are lost until the task notification arrives, which can be 10+ minutes later. Round 1 binds us to flipping the 9 lint-required-foreground scripts to **always-background + propagate**, with the propagation layer becoming authoritative for visibility instead of a fallback.

The mechanism is a paired two-call pattern at each callsite, governed by **explicit filesystem contracts** (the reviewer-rejected `--task-id` design is replaced because shell code cannot observe harness-private task ids — FINDING_1):

1. **Pre-launch path allocation by the calling skill.** Before backgrounding the long script, the skill exports five env vars, all pointing inside its session tmpdir (`$DESIGN_TMPDIR` / `$IMPLEMENT_TMPDIR` / `$REVIEW_TMPDIR`; rejection of symlinks and non-tmpdir paths enforced by helper — FINDING_16):
   - `LARCH_BREADCRUMB_STREAM` — the per-launch breadcrumb file (`<tmpdir>/breadcrumbs/<script>.<launch-id>.ndjson`).
   - `LARCH_DONE_SENTINEL` — empty file path; the child's EXIT trap atomically writes the numeric exit code into the sibling `LARCH_STATUS_FILE` and then `touch`es this sentinel last. Sentinel ownership is **PID-keyed**: `larch_quiet_append_done_trap` records `LARCH_DONE_OWNER_PID=$$` at install time and only touches the sentinel when the trap fires in that PID (FINDING_5).
   - `LARCH_STATUS_FILE` — atomic `EXIT_CODE=<rc>` written before the sentinel via `rename(2)` from a sibling tempfile (FINDING_3).
   - `LARCH_QUIET_LOG_FILE` — passed explicitly so the monitor can find the quiet log to tail on non-zero exit (FINDING_2).
   - `LARCH_BREADCRUMBS_SURFACED_FILE` — empty sentinel path; `lib-quiet.sh` touches it only when it detects FD-3 is actually attached to a real terminal/harness pipe at `larch_quiet_init` time. `breadcrumb-monitor.sh` checks for this file's existence to know whether the harness already streamed lines, and suppresses output only when present (replaces the impossible inherited-env-var guard from FINDING_7 / FINDING_8).
2. **Background launch** via Bash `run_in_background: true`. The script inherits all five env vars.
3. **Foreground consumption call in the same Bash message** — `scripts/breadcrumb-monitor.sh --stream <…> --done-sentinel <…> --status-file <…> --quiet-log <…> --surfaced-sentinel <…>` (no `--task-id` argument exists — FINDING_1). The helper polls these explicit paths, not harness task ids.

The helper uses **Bash `tail -F`-style polling against `wc -c` byte offsets as the primary implemented path** (DECISION_1 thesis is preserved as documented intent, but reviewer FINDING_1 / FINDING_13 require the wc-offset fallback be the actual production code path until a proven Claude Code shell-bridge for Monitor exists). The wc-offset algorithm:

- Track `last_byte_offset` (initialized 0; persisted to a side file alongside the stream path so the loop is restartable).
- Each iteration: `wc -c` the stream file; if growth > 0, read bytes `last_byte_offset+1..new_size`, advance `last_byte_offset` **only after** successful redacted print, and **retain incomplete trailing bytes** (everything after the last newline) for the next iteration so partial records never print torn (FINDING_12, FINDING_13).
- Detect truncation/rotation: if `new_size < last_byte_offset`, reset offset to 0 and emit a `WARN reset` line.
- Poll cadence: default 1.0s (configurable via `--poll-interval`); the 1-second DONE-detect assertion now matches because the loop's polling cadence is ≤1s (FINDING_13).
- Final-drain after observing `LARCH_DONE_SENTINEL` exists: one more wc-offset read + emit, then exit.
- If a documented Monitor-tool shell-bridge ever lands (separate work item — flagged as `OOS` candidate in the design log), `breadcrumb-monitor.sh` can opt in via `--mode monitor`; for now, the production mode is `--mode tail` and the script emits a single `MODE=tail` diagnostic at startup so tests can assert the active path.

**Atomic record writes** (FINDING_12). `emit_breadcrumb` writes one record per single `printf` call with a hard 1 KiB cap (truncate at writer). For concurrent writes from nested helpers, the contract is **per-launch streams** — `LARCH_BREADCRUMB_STREAM` is a path *unique per top-level launch*; nested helpers within that launch inherit it and share one stream. **Across launches**, each top-level skill block allocates a fresh stream. PIPE_BUF atomicity (~4 KiB on macOS) applies to writes into a regular file via O_APPEND, and the 1 KiB record cap stays well under the limit. When a nested helper writes a record exceeding 1 KiB after truncation, the writer emits `WARN truncated` and the next iteration of the monitor reader retains tail bytes (atomicity is guaranteed only per `printf`; tail-byte retention covers the rare oversized case).

**Explicit category API for `emit_breadcrumb`** (FINDING_11). Signature evolves from `emit_breadcrumb TEXT` to `emit_breadcrumb [--category=NAME] TEXT`, with a back-compat shim: when `--category` is omitted, the existing behavior is preserved (no stream record is emitted; the quiet log line still goes to the log file). Stream records (`LARCH_BREADCRUMB_STREAM` set) require an explicit category. The fixed vocabulary `{progress, warn, stall, retry, escalate, wait-ci, network-flake}` is documented in `lib-quiet.md` and enforced by `lib-quiet.sh`'s writer (unknown category → rejected with `WARN unknown-category=<X>` line and the record is dropped from the stream — the quiet log still receives the raw text). The 19 current `emit_breadcrumb` call sites are audited and migrated to pass explicit categories.

**Trap composition** (FINDING_4, FINDING_6). `larch_quiet_install_done_sentinel` is **not** called immediately after `larch_quiet_init`; instead, `lib-quiet.sh` provides `larch_quiet_append_done_trap` which uses a portable trap-chain pattern (capture the current `trap -p EXIT` value, append the sentinel-write logic, re-install). Each of the 9 denylisted scripts adds the call **after** their final script-specific `trap … EXIT` is installed, so the chain composition is guaranteed correct. Wrapper scripts that do NOT currently source lib-quiet (`run-step5-review.sh`, `run-step2-dispatch.sh` — FINDING_6) gain `source "$CLAUDE_PLUGIN_ROOT/scripts/lib-quiet.sh"` + `larch_quiet_init` + `larch_quiet_append_done_trap` at the top, with stdout/stderr regression tests asserting their existing machine-output contract still passes byte-identically.

**Multi-line redaction state** (FINDING_17). `redact-secrets.sh` (or a new sibling helper `scripts/lib-redact-streaming.sh`) gains a "streaming-aware" mode that maintains PEM-block state across input lines — when an opening `-----BEGIN <…>-----` marker is seen, all subsequent lines are buffered (and replaced by a redacted `[REDACTED PEM]` token) until the matching closing marker. The on-failure quiet-log-tail surfacing redacts the **entire** tail as one stream (not per-line independently), so tails that start mid-PEM are still safe. Tests cover full PEM blocks and tails starting mid-key.

**`LARCH_QUIET_DISABLE=1` guard for the stream path** (FINDING_10). `emit_breadcrumb` checks the disable env var **inside its own body**, not only via `larch_quiet_init`, so a caller that toggles disable after init still sees no stream emission. Test case asserts this with `LARCH_QUIET_DISABLE=1 LARCH_BREADCRUMB_STREAM=<path>` → stream file remains empty.

**`ci-wait.sh` progress** (FINDING_15). The script currently emits via `larch_errf` (a stderr-bound API). Convert progress-tier `larch_errf` calls to `emit_breadcrumb --category=wait-ci`, preserving the stderr path for genuine errors via `larch_err` (different category in lib-quiet). This is the most-impactful Family-B script's progress surface, so getting this one right is load-bearing.

**Committed-log redaction path** (FINDING_18). Add a new entry to `scripts/larch-log-batches.tsv` registering the `breadcrumbs/` directory as a sanitizer-required batch. `scripts/larch-log.sh` runs each breadcrumb file through `redact-secrets.sh --streaming` before the file is moved into `larch-logs/<run-id>/breadcrumbs/`. **The committed copy is the redacted copy**; raw streams stay tmpdir-only. Add tests asserting raw secret breadcrumbs never reach committed artifacts.

**SECURITY.md update** (FINDING_19). New section "Breadcrumb stream redaction" covering raw session streams (tmpdir-only), fail-closed monitor redaction (drop line on redactor error), committed-log redaction (mandatory `--streaming` mode), and residual sensitive-content risks (model-actionable breadcrumb categories cannot include secrets by contract).

**Lint AND-semantics** (FINDING_22). The repurposed `lint-foreground-markers.sh` requires per-anchor AND-semantics: the launch fence MUST contain BOTH `run_in_background: true` AND (within same fence OR within 10 Markdown lines after the closing fence) a `breadcrumb-monitor.sh --stream` invocation. Missing either half is a hard-fail. Negative tests for: (a) launch without consumer; (b) consumer without launch; (c) old foreground banner present with otherwise valid pair (must still fail with a "stale phrase" diagnostic — FINDING_23).

**Step 5 anti-polling harness rewrite** (FINDING_24). The existing `scripts/test-step5-foreground.sh` (or equivalent test in the implement test tree) asserts that Step 5 Family B launches must NOT use `run_in_background: true` outside the old foreground-banner pattern. Invert: the harness now asserts every Step 5 Family B launch has BOTH (a) `run_in_background: true` paired with (b) a `breadcrumb-monitor.sh --stream` consumer in the same Bash-block sequence. Keep rejection of unpaired polling loops elsewhere.

**Dynamic Bash 3.2 testing** (FINDING_25). Add a `test-breadcrumb-monitor-bash32` Makefile target that runs the helper under `/bin/bash` (macOS system Bash 3.2) when available, skipping loudly otherwise. Covers offset parsing, partial lines, truncation, absent-stream creation, final drain, and `larch_quiet_append_done_trap` composition. `lint-bash32` stays as the static compatibility gate.

**Makefile / harness shard / agent-lint plumbing** (FINDING_21). New `make test-breadcrumb-monitor` target wired into `.PHONY`, registered in exactly one `test-harnesses-N` shard, added to `docs/linting.md`'s target table, and granted appropriate `agent-lint.toml` allow-list entries beside the existing `test-lib-quiet` / `test-lint-foreground-markers` entries.

**Env-var documentation** (FINDING_9). `lib-quiet.md` gains an explicit env-var table: name, who sets, who reads, exported/inherited semantics, reset semantics per launch, idempotent-init behavior at same PID, `LARCH_QUIET_DISABLE=1` interaction.

**Expanded rewrite surface** (FINDING_20). The plan's "files to modify" list now explicitly enumerates every path that `lint-foreground-markers.sh` static scan + `rg` for the legacy `**⚠ Foreground required` phrase returns: includes `skills/shared/external-reviewers.md`, `skills/research/SKILL.md` (research references), and any `.claude/skills/**/SKILL.md` matches. The pre-merge step exhaustively re-runs the migration scan and adds any new hits.

**Rollout order** (single PR, mechanically staged):

1. Land new infrastructure: `lib-quiet.sh` extension (category API, status-file/done-sentinel/owner-PID/surfaced-file, trap composition helper), `scripts/breadcrumb-monitor.sh` + sibling `.md` + test harness + Bash 3.2 dynamic test, multi-line-aware redaction helper, `scripts/larch-log-batches.tsv` breadcrumb batch row, `larch-log.sh` recursion for the breadcrumbs directory.
2. Update 9 denylisted scripts (call `larch_quiet_append_done_trap` after their final EXIT trap; wrappers `run-step5-review.sh` / `run-step2-dispatch.sh` also gain lib-quiet sourcing; `ci-wait.sh` converts `larch_errf` progress to `emit_breadcrumb --category=wait-ci`). Audit other 17 callers of `emit_breadcrumb` for category compliance.
3. Repurpose `scripts/lint-foreground-markers.sh` with AND-semantics + new banner/comment phrases. Keep behavior **lenient** (warn-only) in this commit.
4. Rewrite every SKILL.md / references / orchestrator-never.md invocation site for the 9 scripts across the expanded surface (per F20). Update the Step 5 anti-polling harness in lockstep (per F24).
5. Flip lint to hard-fail. Run `make lint`, `make lint-foreground-markers`, `make lint-bash32`, `make test-lib-quiet`, `make test-breadcrumb-monitor`, `make test-breadcrumb-monitor-bash32`, the rewritten `make test-lint-foreground-markers`, the rewritten Step 5 harness, the full agent-lint, and the halt-rate regression harness.
6. Update authoring docs: `BASH_AUTHORING.md §4` (rewrite), `AGENTS.md` (Monitor / NEVER bullet update), `SECURITY.md` (new section), `docs/linting.md` (new target row), `docs/run-logs.md` (breadcrumb batch + redacted-commit contract).

## Files to modify/create

### NEW: `scripts/breadcrumb-monitor.sh`

The foreground consumption helper. Argv (FINDING_1, FINDING_2, FINDING_16): `--stream <session-tmpdir-path>`, `--done-sentinel <session-tmpdir-path>`, `--status-file <session-tmpdir-path>`, `--quiet-log <session-tmpdir-path>`, `--surfaced-sentinel <session-tmpdir-path>`, optional `--poll-interval=1.0`, `--rate-cap=5`, `--final-tail-lines=30`, `--mode=tail|monitor` (default `tail`). All path arguments are validated: must be inside one of the session-tmpdir roots (`$DESIGN_TMPDIR` / `$IMPLEMENT_TMPDIR` / `$REVIEW_TMPDIR`); symlinks and non-regular file types are rejected with `larch_err` + exit 2. The helper:

1. On startup, prints one diagnostic line `MODE=<mode>` (test fixtures assert this — FINDING_25 + FINDING_1 transparency).
2. Foreground-duplication guard (FINDING_7, FINDING_8): if `--surfaced-sentinel` path **exists** before the first poll, exit cleanly with no output (harness already streamed FD-3). Otherwise stream.
3. wc-offset loop per the Approach section algorithm (FINDING_12, FINDING_13): incomplete-trailing-bytes retention, truncation/rotation detection, configurable polling cadence.
4. Per-line / per-block redaction via `scripts/lib-redact-streaming.sh` (multi-line PEM state preserved — FINDING_17). Fail-closed: redactor non-zero exit → drop line, log to a `larch_err`-routed diagnostic.
5. On `--done-sentinel` observed: read `EXIT_CODE` from `--status-file`, drain stream one last time, then on non-zero exit emit `--- Failure tail (status=<code>) ---` separator followed by `tail -n <final-tail-lines> <quiet-log>` piped through the same streaming redactor.
6. Bash 3.2-safe primitives only (no `mapfile`/`${var^^}`/associative arrays/namerefs). Internally uses `printf`, `while read`, `wc -c`, `tail -c +N`, `trap EXIT`.
7. Exit codes: 0 success; 2 argv validation; 3 redactor failure (fail-closed); 4 timeout (>30 min without DONE).

### NEW: `scripts/breadcrumb-monitor.md`

Sibling contract per `.claude/rules/script-md-siblings.md`. Documents: argv schema with path-scoping rules (FINDING_16), mode-selection logic (FINDING_25), the wc-offset algorithm (FINDING_12/13), redaction failure semantics (FINDING_17), the env-var interaction table, the `MODE=` diagnostic line, exit codes, and the foreground-duplication guard via the surfaced-sentinel file (FINDING_7).

### NEW: `scripts/test-breadcrumb-monitor.sh`

Offline harness. Cases (FINDING_10, FINDING_12, FINDING_13, FINDING_17, FINDING_25):
- Stream growth → emitted lines reach stdout within ≤1.5 × poll-interval.
- Partial trailing bytes retained between iterations (record split across two writes prints once-complete).
- Stream truncation/rotation → `WARN reset` line + offset resets.
- DONE sentinel observed → loop exits within 1.5 × poll-interval.
- Failure-tail surfaces `<final-tail-lines>` on non-zero `EXIT_CODE` with multi-line PEM redaction intact.
- Surfaced-sentinel present at startup → helper exits silently (FINDING_7).
- Per-line redaction: streaming PEM block fully replaced (FINDING_17).
- Redactor non-zero exit → line dropped, helper continues (fail-closed — FINDING_3 sibling concept).
- Path-scope rejection: `--stream /tmp/outside` → exit 2 (FINDING_16).
- Symlink rejection: `--stream <symlink-to-tmpdir>` → exit 2 (FINDING_16).
- Category enforcement: stream records with unknown category are not propagated.

### NEW: `scripts/test-breadcrumb-monitor.md`

Sibling doc describing coverage.

### NEW: `scripts/test-breadcrumb-monitor-bash32.sh`

Dynamic Bash 3.2 harness (FINDING_25). Runs the same coverage matrix under `/bin/bash` (macOS system Bash 3.2) when present; skips loudly with `larch_err` and exit 0 otherwise. Tests offset parsing, partial-line handling, truncation, absent-stream creation, final drain, and `larch_quiet_append_done_trap` chain composition under real Bash 3.2.

### NEW: `scripts/test-breadcrumb-monitor-bash32.md`

Sibling doc.

### NEW: `scripts/lib-redact-streaming.sh`

Streaming-aware wrapper around `redact-secrets.sh` that maintains multi-line PEM-block state across input lines (FINDING_17). Used by `breadcrumb-monitor.sh` for both per-line stream redaction and final tail redaction. Bash 3.2-safe.

### NEW: `scripts/lib-redact-streaming.md`

Sibling doc describing the streaming-aware redaction contract.

### UPDATED: `scripts/lib-quiet.sh`

- Add `emit_breadcrumb [--category=NAME] TEXT` (FINDING_11) with explicit category enforcement when `LARCH_BREADCRUMB_STREAM` is set; back-compat preserved when no stream is set.
- Add `larch_quiet_append_done_trap` (FINDING_4) using portable trap-chain: capture current `trap -p EXIT` output, append owner-PID + atomic-status-file write + sentinel-touch, re-install. PID-keyed so only the owning process fires (FINDING_5).
- Add `LARCH_DONE_OWNER_PID` env var recorded at trap install time (FINDING_5).
- Add `LARCH_QUIET_DISABLE=1` check inside `emit_breadcrumb` itself, not only `larch_quiet_init` (FINDING_10).
- Add FD-3-visibility detection at `larch_quiet_init` that `touch`es `LARCH_BREADCRUMBS_SURFACED_FILE` when stdout is a tty or a known harness pipe (FINDING_7).
- Add depth tracking via `LARCH_BC_DEPTH` env, incremented only on new PID (FINDING_9).
- All additions remain env-var-gated → legacy callers unchanged.

### UPDATED: `scripts/lib-quiet.md`

Document everything new with an explicit env-var table (FINDING_9): `LARCH_BREADCRUMB_STREAM`, `LARCH_DONE_SENTINEL`, `LARCH_STATUS_FILE`, `LARCH_QUIET_LOG_FILE`, `LARCH_BREADCRUMBS_SURFACED_FILE`, `LARCH_DONE_OWNER_PID`, `LARCH_BC_DEPTH`, `LARCH_QUIET_DISABLE`. For each: who sets, who reads, export/inheritance/reset semantics, idempotency rules. Document the structured record format (`larch:bc t=… d=… p=… s=… c=… text=…`), the category vocabulary, the 1 KiB record cap, the truncation/rotation contract, and the trap-chain semantics.

### UPDATED: `scripts/test-lib-quiet.sh`

Add cases for: explicit `--category` argument, category enforcement (unknown rejected), `LARCH_QUIET_DISABLE=1` + stream set → no records (FINDING_10), `larch_quiet_append_done_trap` composes with later-installed traps (FINDING_4), PID-keyed sentinel ownership (FINDING_5 — child PID fires its own trap, parent PID fires only its own), and `LARCH_BREADCRUMBS_SURFACED_FILE` touched only when FD-3 visibility detected (FINDING_7). Add regression assertion: legacy callers see byte-identical output to pre-change behavior.

### UPDATED: `scripts/redact-secrets.sh`

Add `--streaming` mode flag (FINDING_17). In streaming mode, the input may be split across multiple invocations; the redactor maintains state via a `--state-file` argument. Existing one-shot mode unchanged for back-compat.

### UPDATED: `scripts/test-redact-secrets.sh`

New cases for streaming-mode PEM block (FINDING_17): complete block in one input → fully redacted; block split across two inputs sharing a state file → still fully redacted; tail starting mid-PEM (no opening marker visible) → conservatively redacts up to next blank line. Plus regression: one-shot mode behavior unchanged.

### REWRITTEN: `scripts/lint-foreground-markers.sh`

Same path. New contract per FINDING_22: per-anchor AND-semantics. Denylist of 9 script basenames unchanged. New required-banner phrase: `**⚠ Background required — must be paired with breadcrumb-monitor.sh.**`. New per-anchor comment: `# Background pair required: see BASH_AUTHORING.md §4`. New per-anchor structural rule: launch fence MUST contain `run_in_background: true` AND a `breadcrumb-monitor.sh --stream` invocation within same fence OR within 10 Markdown lines after closing fence. Violations: `<path>:<line>: missing background-pair half (<half>) for <basename>` to stderr.

### REWRITTEN: `scripts/lint-foreground-markers.md`

Rewrite contract docs to match the AND-semantics + new phrases + look-forward window (FINDING_22).

### UPDATED: `scripts/test-lint-foreground-markers.sh`

Rewrite cases (FINDING_22, FINDING_23):
- Launch + paired Monitor in same fence → pass.
- Launch without consumer → fail with `missing background-pair half (consumer)`.
- Consumer without launch → fail with `missing background-pair half (launch)`.
- Old `**⚠ Foreground required` banner present with otherwise-valid pair → fail with `stale foreground-marker phrase`.
- Old `# Foreground required:` comment present with otherwise-valid pair → fail same way.
- Adjacent-fence consumer within 10-line window → pass.
- Adjacent-fence consumer outside window → fail.

### UPDATED: `BASH_AUTHORING.md`

Rewrite §4 ("Background+propagate markers for blocking Family B script calls"): describe the bg+pair contract, document the new banner/comment phrases, explain the AND-semantics, reference DECISION_1/DECISION_2. Remove old "foreground required" wording.

### UPDATED: `AGENTS.md`

Update the "Don't spawn a Monitor or polling loop" bullet to carve out the new background+paired-Monitor pattern as the supported case for Family B. Cross-reference the new `scripts/breadcrumb-monitor.md`.

### UPDATED: `SECURITY.md`

New section "Breadcrumb stream redaction" (FINDING_19): documents raw-stream tmpdir-only storage; fail-closed monitor redaction (line dropped on redactor error); mandatory `--streaming` redaction before commit; residual sensitive-content risk discussion (categories cannot contain secrets by contract).

### UPDATED: `skills/shared/orchestrator-never.md`

Adjust canonical NEVER #9 / #16 narratives to reflect that the 9 denylisted scripts are now expected to background AND propagate, and the failure mode being prevented (turn-ending before task notification) is handled by the paired Monitor consumer rather than by foreground execution.

### UPDATED: `skills/implement/SKILL.md`

Rewrite every invocation site of the 9 denylisted scripts. NEVER #9 / NEVER #16 updated in lockstep with `orchestrator-never.md`.

### UPDATED: `skills/design/SKILL.md`

Same rewrite for /design callsites (sketch collection, dialectic collection, plan-review-loop, etc.). Update the "Don't spawn a Monitor or…" mention in the Conventions block.

### UPDATED: `skills/design/references/plan-review.md`, `skills/design/references/dialectic-execution.md`, `skills/design/references/sketch-launch.md`

Rewrite embedded fenced examples carrying the old foreground-banner pattern.

### UPDATED: `skills/review/references/heavy-worker.md`

Rewrite Wait Discipline examples that quote the old pattern for `collect-agent-results.sh`, `dispatch-with-waterfall.sh`, `dispatch-plan-voters.sh`.

### UPDATED: `skills/review-and-fix/SKILL.md`

Same rewrite for the `review-and-fix.sh` invocation site and any heavy-worker re-quotes.

### UPDATED: `skills/shared/dialectic-protocol.md`, `skills/shared/voting-protocol.md`, `skills/shared/external-reviewers.md`

Rewrite embedded fenced examples carrying the old pattern (FINDING_20 expansion includes `external-reviewers.md`).

### UPDATED: `skills/research/SKILL.md`

Rewrite any embedded references to the old foreground pattern (FINDING_20).

### UPDATED: `.claude/skills/*/SKILL.md` and `.claude/rules/*.md` (case-by-case)

For each path the `lint-foreground-markers.sh` static scan or `rg "Foreground required"` returns, apply the rewrite. The pre-merge step exhaustively re-runs the scan to catch any newly-introduced files.

### UPDATED: `docs/linting.md`

Document the repurposed `lint-foreground-markers` target's new contract. Add a new target row for `test-breadcrumb-monitor` and `test-breadcrumb-monitor-bash32` (FINDING_21).

### UPDATED: `docs/run-logs.md`

Document the new `breadcrumbs/` per-run directory and the mandatory `--streaming` redaction step that produces the committed copy (FINDING_18). Note that the committed copy is the redacted copy; raw streams stay tmpdir-only.

### UPDATED: `scripts/larch-log-batches.tsv` and `scripts/larch-log-batches.md`

Add a new row registering the `breadcrumbs/` directory under each per-run log root, with the `--streaming`-redaction requirement (FINDING_18).

### UPDATED: `scripts/larch-log.sh`

Walk the `breadcrumbs/` subdirectory (recursive) for the registered batch; pipe each file through `redact-secrets.sh --streaming --state-file <tmp>` before placing the redacted output in `larch-logs/<run-id>/breadcrumbs/<basename>`. Fail-closed on redactor error.

### UPDATED: `scripts/test-larch-log.sh`

New cases asserting: (a) raw secret breadcrumbs in tmpdir never reach the committed copy; (b) PEM blocks in breadcrumb stream files survive multi-line redaction; (c) redactor non-zero exit fails the larch-log step (fail-closed).

### UPDATED: `Makefile`

Add `.PHONY` and recipes for `test-breadcrumb-monitor`, `test-breadcrumb-monitor-bash32` (FINDING_21). Add to the existing `test-harnesses-<N>` shard (one shard only — confirmed by shard-coverage guard).

### UPDATED: `agent-lint.toml`

Add allow-list entries for `scripts/breadcrumb-monitor.sh`, `scripts/breadcrumb-monitor.md`, `scripts/test-breadcrumb-monitor.sh`, `scripts/test-breadcrumb-monitor.md`, `scripts/test-breadcrumb-monitor-bash32.sh`, `scripts/test-breadcrumb-monitor-bash32.md`, `scripts/lib-redact-streaming.sh`, `scripts/lib-redact-streaming.md` — beside existing test-lib-quiet / test-lint-foreground-markers entries (FINDING_21).

### UPDATED: Step 5 anti-polling harness (path TBD per current repo layout — e.g., `skills/implement/scripts/test-step5-foreground.sh` or `scripts/test-step5-foreground.sh`)

Rewrite assertions (FINDING_24): every Step 5 Family B launch must have BOTH (a) `run_in_background: true` AND (b) paired `breadcrumb-monitor.sh --stream` consumer in the same Bash-block sequence. Continue rejecting unpaired polling loops elsewhere.

### UPDATED: 9 denylisted scripts

- `scripts/ship-pr.sh`, `scripts/ci-wait.sh`, `scripts/collect-agent-results.sh`, `scripts/dispatch-plan-voters.sh`, `scripts/dispatch-with-waterfall.sh`, `scripts/run-step5-review.sh`, `skills/implement/scripts/run-step2-dispatch.sh`, `skills/implement/scripts/step2-implement.sh`, `skills/review-and-fix/scripts/review-and-fix.sh`: each adds `larch_quiet_append_done_trap` **after** the final script-specific EXIT trap (FINDING_4).
- `run-step5-review.sh`, `run-step2-dispatch.sh`: also gain `source "$CLAUDE_PLUGIN_ROOT/scripts/lib-quiet.sh"` + `larch_quiet_init` at the top, with regression tests asserting stdout/stderr remain byte-identical (FINDING_6).
- `ci-wait.sh`: convert progress-tier `larch_errf` calls to `emit_breadcrumb --category=wait-ci` (FINDING_15).
- 17 other `emit_breadcrumb` callers (across `scripts/` and `skills/*/scripts/`): audited and migrated to pass explicit `--category=` flag matching the closest member of the fixed vocabulary (FINDING_11).

## Edge cases

- **Foreground-duplication guard via filesystem sentinel** (FINDING_7, FINDING_8): when harness actually runs the launch foreground, `lib-quiet.sh`'s `larch_quiet_init` `touch`es `LARCH_BREADCRUMBS_SURFACED_FILE` if FD-3 detects a tty/harness pipe. `breadcrumb-monitor.sh` checks for the file's existence at startup; if present, exits silently. Tests exercise both branches (background → file absent → monitor streams; foreground → file present → monitor silent).
- **Per-launch stream isolation** (FINDING_12): each top-level launch gets a fresh `LARCH_BREADCRUMB_STREAM` path; nested helpers within that launch share it (per design). Across launches, streams are independent. No global breadcrumb file.
- **Stream growth bound**: soft 10 MB cap enforced by monitor (warn + truncate-front when exceeded). Per-record cap 1 KiB enforced by writer (truncate at writer with `WARN truncated`).
- **Subagent visibility**: Agent-tool subagents (used by `/review --subagent`, `/design` heavy workers) execute the launch+monitor pair entirely inside their own Bash tool calls. The helper script is repo-local so accessible. Documented in `skills/review/references/heavy-worker.md`.
- **Redaction failure fail-closed** (FINDING_17): both `breadcrumb-monitor.sh` and `larch-log.sh` drop the line / fail the step (respectively) on redactor non-zero exit.
- **`LARCH_QUIET_DISABLE=1` interaction** (FINDING_10): the new stream emission target is gated inside `emit_breadcrumb` itself, not only at `larch_quiet_init` time. Test harness asserts.
- **Backwards compatibility for legacy callers**: scripts that do NOT set any of the new env vars see byte-identical pre-change behavior in `lib-quiet.sh` (purely additive paths gated on env var presence).
- **Nested helpers — sentinel ownership** (FINDING_5): only the original-launch PID's EXIT trap fires the sentinel write; nested helpers' EXIT traps fire their own per-PID logic without clobbering the parent's. Tested via a parent script that backgrounds an inner denylisted script and asserts the outer sentinel is NOT touched by the inner script.
- **Trap chain composition** (FINDING_4): `larch_quiet_append_done_trap` reads the current trap via `trap -p EXIT`, parses its body via a single sed, appends the new logic, and re-installs. Tested with a fixture script that installs `trap 'rm -f $TMP' EXIT` before calling the helper and asserts both `rm` and the sentinel write fire.

## Failure modes

1. **Stream growth outpaces monitor read** (sustained > 5 lines/sec). Earliest warning: the rate-cap counter in `breadcrumb-monitor.sh` triggers and emits a `WARN rate-capped` line; bytes are still consumed via offset advance but only the rate-capped sample is printed to chat. Mitigation: built-in rate-cap (default 5 lines/sec, `--rate-cap` override) ensures chat is not flooded; the offset bookkeeping still tracks ground truth so committed-log redaction sees the full stream.
2. **Dual-runner ordering — author forgets paired Monitor consumer** (FINDING_22). Earliest warning: `lint-foreground-markers.sh` AND-semantics catches the missing half in pre-commit with a precise diagnostic naming which half is absent. Mitigation: lint is hard-fail after rollout step 5, so missing pair blocks merge. Step 5 anti-polling harness (FINDING_24) provides an in-test sanity check.
3. **Redactor failure leaks secrets to chat**. Earliest warning: `breadcrumb-monitor.sh` exits with code 3 (redactor failure) and the line is dropped (fail-closed — FINDING_17). Mitigation: fail-closed contract documented in `breadcrumb-monitor.md`, `SECURITY.md`, and tested. The committed-log path also fails closed (FINDING_18), so even if the streaming path were to misbehave, the committed copy is never raw.

## Testing strategy

- `test-lib-quiet.sh`: extended cases per F4, F5, F7, F9, F10, F11 (above).
- `test-breadcrumb-monitor.sh`: full coverage per F1, F7, F8, F12, F13, F16, F17, F25 (above).
- `test-breadcrumb-monitor-bash32.sh`: dynamic Bash 3.2 coverage per F25.
- `test-redact-secrets.sh`: streaming-mode PEM coverage per F17.
- `test-lint-foreground-markers.sh`: AND-semantics + stale-phrase fixtures per F22, F23.
- `test-larch-log.sh`: breadcrumb-batch redaction asserting raw secrets never commit (F18).
- Updated Step 5 anti-polling harness per F24.
- Manual smoke test: run `/design --simple` and `/implement` on a tiny issue end-to-end. Verify the user sees breadcrumbs in chat during a backgrounded `collect-agent-results.sh`. Verify failure-tail surfaces on non-zero exit.
- CI: `make lint`, `make lint-foreground-markers`, `make lint-bash32`, `make test-lib-quiet`, `make test-breadcrumb-monitor`, `make test-breadcrumb-monitor-bash32`, `make test-lint-foreground-markers`, `make test-larch-log`, plus the rewritten Step 5 harness, agent-lint, and the halt-rate regression harness must all pass.
- Halt-rate regression: the foreground-markers rule was originally added because of #2454-class incidents where backgrounded scripts ended the turn before result handling. The paired Monitor consumer is itself foreground and the wc-offset loop waits on the DONE sentinel, so turn coupling is restored. The halt-rate harness gates merge.

diff_lines: 1150


## Acceptance

- All 24 Step 3 accepted findings are reflected in the implementation contracts.
- DECISION_1 (Monitor + wc-offset fallback) and DECISION_2 (explicit skill-level pairing) from `dialectic-resolutions.md` are followed.
- Round 1 binding constraints (broad coverage, inline-chat display, foreground-duplication guard, flip 9 scripts to background+propagate, failure UX with exit code + stderr tail, max refactor budget, model-actionable categories, transparent nested propagation) all addressed in the Approach section.
- `make lint`, `make lint-foreground-markers`, `make lint-bash32`, `make test-lib-quiet`, `make test-breadcrumb-monitor`, `make test-breadcrumb-monitor-bash32`, `make test-redact-secrets`, `make test-lint-foreground-markers`, `make test-larch-log`, the rewritten Step 5 anti-polling harness, agent-lint, and the halt-rate regression harness all pass on CI before merge.
- The full mermaid architecture diagram (committed alongside this plan) accurately reflects the launch + monitor + redact + commit topology.
- After rollout step 5 (hard-fail lint flip), no callsite of the 9 denylisted scripts ships without a paired `breadcrumb-monitor.sh` consumer.

diff_lines: 1150

## Test plan
(no test plan section in plan-file)
