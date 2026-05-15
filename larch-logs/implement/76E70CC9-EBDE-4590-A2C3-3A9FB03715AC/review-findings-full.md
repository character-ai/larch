### FINDING_1: panel [plan-review/accepted]

## review-core.sh loop/resume protocol

- **Concern**: `review-core.sh` is planned to emit `REVIEW_FIX_REQUIRED=true` so the SKILL.md wrapper can invoke `/review-and-fix`, but then expects to continue "after fix confirmation" and loop back to Stage 2. A bash process cannot yield to a Skill tool and resume its internal loop unless there is an explicit resumable protocol with persisted round state. This is a fundamental subprocess boundary mismatch.
- **Reviewer(s)**: Cursor-Innovation, Codex-Arch, Codex-Edge, Codex-Innovation, Codex-Pragmatic, Codex-Requirements, codex-fallback-cursor-Arch, codex-fallback-cursor-Edge, codex-fallback-cursor-Requirements
- **Suggested revision to the plan**: Make the wrapper own the outer round loop, calling `review-core.sh` as a single-round engine that exits with `fix-required` and stores round state. The wrapper invokes `/review-and-fix`, then re-invokes `review-core.sh` for the next round with explicit state input (round number, prior artifact paths).

### FINDING_10: panel [plan-review/accepted]

## PANEL_MODE overloaded — simple|hard topology vs normal|both-down availability

- **Concern**: `dispatch-panel.sh` currently emits `PANEL_MODE=normal|both-down` to signal reviewer availability (driving voting behavior). The plan has `--panel simple|hard` also wanting to use `PANEL_MODE` for topology shape. Changing `PANEL_MODE` to `simple` or `hard` would break the `both-down` voting shortcut; keeping `both-down` hides the requested panel shape.
- **Reviewer(s)**: Codex-Arch
- **Suggested revision to the plan**: Keep `PANEL_MODE=normal|both-down` for availability semantics and add a separate `PANEL_SHAPE=simple|hard` output KV from `dispatch-panel.sh`. Update `dispatch-panel.md` and `test-dispatch-panel.sh` accordingly.

### FINDING_11: panel [plan-review/accepted]

## Parent tmpdir artifact preservation incomplete

- **Concern**: The plan's Constraints state that `/implement`'s dependency on nested review artifacts is preserved, but `emit-tally.sh` currently only copies `review-round-summary.md` and `review-summary.json` to `$(dirname "$SESSION_ENV_PATH")/`. The `/implement` flow also needs `rejected-findings.md`, `review-dirty-tree-summary.env`, and `oos-accepted-review.md` at the parent tmpdir. These copies are currently done inline in SKILL.md but the plan does not assign them to `review-core.sh` or the wrapper explicitly.
- **Reviewer(s)**: Codex-Requirements, codex-fallback-cursor-Arch
- **Suggested revision to the plan**: Add explicit parent-tmpdir copy steps to Step 1 (`review-core.sh`) or Step 2 (wrapper Step 4): copy `rejected-findings.md`, `review-dirty-tree-summary.env`, and `oos-accepted-review.md` to `$(dirname "$SESSION_ENV_PATH")` when `SESSION_ENV_PATH` is non-empty.

### FINDING_12: panel [plan-review/accepted]

## Heavy-worker divergence widened by leaving it unchanged

- **Concern**: `skills/review/references/heavy-worker.md` Step 1 names `gather-branch-context.sh`, while inline `/review` uses `gather-context.sh`. The plan leaves heavy-worker unchanged while centralizing inline logic in `review-core.sh`. This widens an existing documentation-level divergence into a code-level one, risking wrong entrypoint, missing KVs, or unhealthy subagent improvisation.
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, codex-fallback-cursor-Arch
- **Suggested revision to the plan**: Add a note to Step 1 or Step 2: reconcile the heavy-worker gather entrypoint to `gather-context.sh` (or route both paths through `review-core.sh`) in the same PR, or explicitly document this divergence as a known gap deferred to Part 2.

### FINDING_14: panel [plan-review/accepted]

## dispatch-panel.sh --panel tests need injectable launch stub

- **Concern**: `test-dispatch-panel.sh` tests for `--panel simple|hard` slot counts will need to invoke `launch-review.sh` with `--tool cursor` or `--tool codex`. External reviewer launches are hard-coded to `$PLUGIN_ROOT/scripts/launch-review.sh` (unlike Claude which has `--launch-claude-subprocess`). Without a test seam, slot-count assertions require real Cursor/Codex availability or only exercise the both-down path.
- **Reviewer(s)**: codex-fallback-cursor-Edge, codex-fallback-cursor-Requirements
- **Suggested revision to the plan**: Add a `--launch-review` test override flag to `dispatch-panel.sh` (analogous to the existing `--launch-claude-subprocess` flag) and use a stub in `test-dispatch-panel.sh` for simple/hard topology assertions.

### FINDING_2: panel [plan-review/accepted]

## Post-fix relevant-checks and classification dropped

- **Concern**: The plan's fix path (Stage 3g, then loop back to Stage 2) drops the current Step 3e `run-relevant-checks-captured.sh` and substantial/non-substantial re-review classification gate. After fixes, the existing flow requires: run relevant-checks, handle `STATUS=fail` / `REDACTED_LOG_FILE`, retry until clean, classify substantiality, then decide exit vs re-review. Without this, broken fixes can bypass the test gate and re-dispatch reviewers against a broken tree.
- **Reviewer(s)**: Cursor-Innovation, Codex-Arch, Codex-Edge, Codex-Innovation, Codex-Pragmatic, Codex-Requirements, codex-fallback-cursor-Arch, codex-fallback-cursor-Edge, codex-fallback-cursor-Requirements
- **Suggested revision to the plan**: Add to Step 2 (SKILL.md wrapper): after `/review-and-fix` returns, the wrapper runs `run-relevant-checks-captured.sh --site review-step3e --tmpdir "$REVIEW_TMPDIR"`, handles failures/retry, and classifies the fixed round as substantial or non-substantial before deciding to loop or terminate.

### FINDING_3: panel [plan-review/accepted]

## reviewer-aggregator.md and reviewer-judge.md match reviewer-*.md glob

- **Concern**: `scripts/generate-pre-rendered-reviewer-prompts.sh` walks `agents/` with `find … -name 'reviewer-*.md'`. The planned `agents/reviewer-aggregator.md` and `agents/reviewer-judge.md` match this glob. They would be treated as external specialist agents, causing generator drift (`check-generators.sh` or `--check` mode), potentially bloating pre-rendered inputs for agents never passed to `launch-review.sh`, and breaking CI.
- **Reviewer(s)**: Cursor-Pragmatic, Codex-Edge, codex-fallback-cursor-Arch, Cursor-Innovation
- **Suggested revision to the plan**: Either rename the agents outside the `reviewer-*` namespace (e.g., `orchestrator-aggregator.md`, `orchestrator-judge.md`), or update `generate-pre-rendered-reviewer-prompts.sh` with an exclusion list for non-specialist orchestration agents and document this in the file-change summary.

### FINDING_4: panel [plan-review/accepted]

## Makefile targets not planned for new test harnesses

- **Concern**: Step 7 of the plan requires `make test-review-core` and `make test-review-and-fix`, but the file-change summary does not include `Makefile`. These targets currently do not exist and have no `.PHONY`, recipe, or shard wiring. Per `docs/linting.md` and the repo pattern (`test-harnesses-N` shards), new harnesses must be added to `Makefile` and wired into a shard before they can run in CI.
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Codex-Arch, Codex-Edge, Codex-Innovation, Codex-Pragmatic, Codex-Requirements, codex-fallback-cursor-Edge, codex-fallback-cursor-Requirements
- **Suggested revision to the plan**: Add `Makefile` to the file-change summary. Include `.PHONY` entries, target recipes for `test-review-core`, `test-review-and-fix`, and `test-call-fixer`, and wire them into an appropriate `test-harnesses-N` shard.

### FINDING_5: panel [plan-review/accepted]

## gather-context.sh flag mismatch (--review-tmpdir vs --output-dir)

- **Concern**: Step 1 of the plan lists `--review-tmpdir DIR` as a flag for `gather-context.sh`, but the script's actual usage is `--output-dir DIR` (with optional `--description-text` and `--scope-files`). The first implementation pass would fail with an argument parsing error on Stage 1.
- **Reviewer(s)**: Cursor-Innovation
- **Suggested revision to the plan**: Fix the flag table in Step 1 to use `--output-dir "$REVIEW_TMPDIR"` (or add a thin adapter in `review-core.sh` that maps the name).

### FINDING_6: panel [plan-review/accepted]

## test-review-structure.sh hard-codes 7-script count

- **Concern**: `scripts/test-review-structure.sh` lines 65-75 assert `"${#review_scripts[@]}" -eq 7` and enumerate seven scripts. Adding `review-core` requires bumping this to 8 and updating the accompanying comment. The plan Step 6 mentions adding `review-core` to the array but does not mention the count invariant — omitting it causes CI failure even when all files exist.
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Suggested revision to the plan**: Add an explicit note in Step 6 to bump the expected length to 8 in `test-review-structure.sh` when extending the `review_scripts` array.

### FINDING_8: panel [plan-review/accepted]

## Run-log (log-phase.sh) ownership duplicated

- **Concern**: Step 1 of the plan puts `log-phase.sh` calls inside `review-core.sh` Stage 4 when `RUN_ID` is set. Step 2 says the thin SKILL.md wrapper runs Step 4 "exactly as today" — and current SKILL.md Step 4d already calls `log-phase.sh` for review batches. This creates double batch writes, or the log may be written before final summary artifacts are complete.
- **Reviewer(s)**: Cursor-Pragmatic, Codex-Innovation, Codex-Requirements, codex-fallback-cursor-Edge
- **Suggested revision to the plan**: Assign run-log batch ownership to exactly one layer. Prefer SKILL.md Step 4d (after all summary artifacts are complete); remove or conditionally skip the Stage 4 logging inside `review-core.sh`, and document this in `review-core.md`.

### FINDING_9: panel [plan-review/accepted]

## Dirty-tree recovery contract underspecified in review-core.sh

- **Concern**: The plan lists `review-dirty-tree-summary.env` as an artifact of `review-core.sh` but does not specify the recovery flow: scan every reviewer `${output}.dirty-tree` sidecar, run `check-mid-run-dirty-tree.sh --mode checkpoint`, aggregate path streams, auto-discard reviewer-introduced changes, track `RECOVERY_TAKEN`, and copy the full summary to `$(dirname "$SESSION_ENV_PATH")/review-dirty-tree-summary.env` when nested. Without this, reviewer-introduced working-tree changes can remain, mixing into main-agent fixes or causing `/implement`'s recovery to see wrong state.
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Cursor-Pragmatic, Codex-Pragmatic, Codex-Requirements, codex-fallback-cursor-Edge, codex-fallback-cursor-Requirements
- **Suggested revision to the plan**: Add an explicit dirty-tree recovery stage to Step 1 (`review-core.sh`) after collection (sidecar scan, checkpoint, discard/log, path-stream aggregation, parent artifact copy). Add harness cases for clean, dirty, and unknown sidecars.

### REJ_P1: FINDING_7 (Cursor-Innovation, Codex-Edge, Codex-Innovation, Codex-Pragmatic, Codex-Requirements, codex-fallback-cursor-Arch) [plan-review/rejected]

**Finding**: `/review-and-fix` applies accepted reviewer prose to `Edit`/`Write` operations but the plan does not define untrusted-input boundaries. `collect-findings.sh` preserves raw reviewer body text into `- **Concern**`, so a malicious or compromised reviewer output could embed instructions that the main agent follows during fixing. Additionally, no path validation rules are defined — the fixer could steer edits to symlinks, absolute paths, or submodule paths contrary to `.claude/rules/no-direct-submodule-edits.md`. Per SECURITY.md, security-relevant behavior changes require an update. The finding proposed: treat finding text as untrusted data, parse only structured fields, validate repo-relative non-symlink non-submodule non-absolute non-`..` paths, fence reviewer prose with collision-resistant XML delimiters, and update SECURITY.md.
**Reason not implemented**: The panel voted EXONERATE (1 YES, 2 EXONERATE). The concern is legitimate but the proposed full scope (XML fencing, exhaustive path validation spec, SECURITY.md update) is disproportionate for what is an internal-only skill not accepting external reviewer input directly. The plan already includes path safety requirements in `call-fixer.md` (Step 4). The fencing and SECURITY.md update can be addressed when the skill is promoted to handle truly external input.

### REJ_P2: FINDING_13 (codex-fallback-cursor-Requirements) [plan-review/rejected]

**Finding**: The current `test-review-structure.sh` has assertions that pin literals inside `SKILL.md` (substantive validation, `render-specialist-prompt.sh`, `--pieces-json`, Gemini negative pins, OOS security exclusions, two-mode grammar, etc.). Replacing SKILL.md with a ~50-line wrapper will likely move or remove those literals. Step 6 of the plan only plans to add new assertions, not provide an assertion-by-assertion migration plan showing which literals stay in SKILL.md vs get retargeted. This creates risk that CI catches failures only after the fact.
**Reason not implemented**: The panel voted EXONERATE (1 YES, 2 EXONERATE). The concern is real, but an explicit assertion-by-assertion migration matrix is process overhead that CI and targeted harness updates will handle naturally. The plan Step 6 already includes a migration plan section with the key literals. The thin wrapper must preserve all asserted literals (or the plan explicitly notes where each moves), so the concern is addressed at the implementation level without needing a separate pre-implementation enumeration.

### REJ_P3: FINDING_15 (codex-fallback-cursor-Edge) [plan-review/rejected]

**Finding**: `review-and-fix.sh` calls `call-fixer.sh` for each finding and expects `FIXER_STATUS=applied|skipped`, but there is no per-finding selector or verification that Edit/Write actually changed the tree. The same finding block could be processed repeatedly or `applied` could be emitted without any actual edit occurring.
**Reason not implemented**: The panel voted EXONERATE (1 YES, 2 EXONERATE). The concern about per-finding verification is valid but adding a mandatory tree diff verification step adds significant loop complexity. The basic contract (per-finding IDs passed to call-fixer.sh, SKILL.md wrapper applies edits) is sufficient for the first pass. Verification and idempotency guards are appropriate for Part 2 when the fixer contract is exercised in more scenarios.

