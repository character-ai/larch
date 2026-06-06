### FINDING_1:
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:47-54
- **Concern**: Step 0 post-invoke parent rehydration fence omits closing fi for outer if. Scenario: The proposed block opens if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ]; then, nests a plugin-root.env source, then jumps straight to export CLAUDE_PLUGIN_ROOT without fi; both Step 0 fences would be a bash syntax error and Step 0 cannot run
- **Proposed resolution**: Close the outer if before export: after the inner fi add fi, then export CLAUDE_PLUGIN_ROOT (initial and dirty-tree resume insertion points)

### FINDING_2:
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:311-318,380-388
- **Concern**: Finding 1: proposed Step 0 parent rehydration block is missing the closing fi for the outer CLAUDE_PLUGIN_ROOT check. Scenario: Following the plan inserts a syntactically invalid Bash fence in both initial and dirty-tree resume Step 0 paths, so Step 0 fails before parse-bootstrap-routing-envelope.sh can be sourced.
- **Proposed resolution**: Close the outer if before export CLAUDE_PLUGIN_ROOT in the proposed block.

### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:115,770-795; scripts/test-implement-timing-rehydration.sh:153-156
- **Concern**: Finding 2: Step 5 fence merge removes one canonical plugin-root source guard but the plan leaves the hard-coded guard count and prose at 42. Scenario: make test-implement-timing-rehydration will count 41 guards after the standalone Step 5 fence and run fence become one fence, causing the required harness to fail.
- **Proposed resolution**: Update the literal expected count and adjacent SKILL.md count text to 41 as part of the same Step 5 edit.

### FINDING_4:
- **Reviewer(s)**: Cursor-Edge, Cursor-dyn-shell-fence-flow, Cursor-dyn-contract-sync
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:46-54
- **Concern**: Step 0 post-invoke rehydration snippet is missing the outer `fi`. Scenario: The proposed block closes the inner `if` but never closes `if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ]`; `export CLAUDE_PLUGIN_ROOT` sits inside an unclosed `if`, so both Step 0 fences fail bash syntax check before routing parse runs
- **Proposed resolution**: Close the outer `if` before `export CLAUDE_PLUGIN_ROOT` (export should run unconditionally after the conditional source)

### FINDING_5:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-implement-timing-rehydration.sh:153-156
- **Concern**: Step 5 fence merge changes the plugin-root source guard count but the plan does not update the pinned structural test. Scenario: Deleting the standalone Step 5 telemetry fence and merging it with the run-step5-review fence removes one exact plugin-root.env guard, so make test-implement-timing-rehydration will still expect 42 and fail
- **Proposed resolution**: Update the expected plugin_root_source_count to the post-change count, or keep the guard cardinality unchanged if that is intentional

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation, Cursor-dyn-harness-wiring
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:46-54
- **Concern**: Step 0 post-invoke parent rehydration fence is missing a closing fi for the outer if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] block. Scenario: The proposed insertion ends the inner if with fi then immediately has export CLAUDE_PLUGIN_ROOT still inside the unclosed outer if; both initial and dirty-tree resume Step 0 fences will fail bash -n / runtime syntax check before parse-bootstrap-routing-envelope.sh runs
- **Proposed resolution**: Add fi before export CLAUDE_PLUGIN_ROOT so the block reads: outer if → parse _inv_tmpdir → inner if source plugin-root.env → fi → fi → export CLAUDE_PLUGIN_ROOT

### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:311-318,380-388
- **Concern**: [SCOPE-REDUCTION] Step 0 parent rehydration expands the SKILL.md surface beyond the approved Step 5-only edit and contradicts the plan's own "No Step 0 SKILL fallback" statement. Scenario: The PR would touch two Step 0 bootstrap fences and introduce a new plugin-root sourcing path that is not part of the SIMPLE approved scope; as written in the plan, that block is also syntactically incomplete because the outer if lacks a closing fi
- **Proposed resolution**: Drop the Step 0 parent rehydration edit and keep the wrapper self-derive/export fix plus its harness/doc updates; only add a separate tested Step 0 fence change if a post-bootstrap parent-parse failure is reproduced

### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-dyn-harness-wiring
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-implement-timing-rehydration.sh:155-156
- **Concern**: Step 5 fence merge drops one plugin-root guard but harness still expects 42. Scenario: make test-implement-timing-rehydration fails after SKILL.md edit; acceptance gate in plan blocks merge
- **Proposed resolution**: Decrement pinned guard count to 41 and update skills/implement/SKILL.md:115 site-count prose in the same PR

### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: nit
- **Focus area**: risk-integration
- **Location**: Makefile:plan.txt:192-199
- **Concern**: New test-append-execution-issue target has no named harness shard. Scenario: test-harness-shards-coverage fails if implementer adds recipe only
- **Proposed resolution**: Add test-append-execution-issue to a specific test-harnesses-N line (e.g. test-harnesses-14) and .PHONY in the plan

### FINDING_10:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-implement-timing-rehydration.sh:154-156; skills/implement/SKILL.md:770-790
- **Concern**: Plan deletes one canonical plugin-root source guard but does not update the hard-coded rehydration cardinality test. Scenario: Implementing the Step 5 fence merge as planned drops the source-guard count from 42 to 41, so make test-implement-timing-rehydration fails
- **Proposed resolution**: Update the expected count and matching SKILL.md prelude count, or preserve the guard count intentionally

### FINDING_11:
- **Reviewer(s)**: Cursor-dyn-scope-control
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:46-54
- **Concern**: Step 0 post-invoke rehydration fence snippet is syntactically invalid (outer if never closed). Scenario: Pasting the plan fence into SKILL.md breaks Step 0 with a bash parse error before routing parse runs
- **Proposed resolution**: Add the missing closing fi for the outer if before export CLAUDE_PLUGIN_ROOT and verify both initial and resume fences shellcheck clean

### FINDING_12:
- **Reviewer(s)**: Cursor-dyn-scope-control
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:298-318
- **Concern**: [SCOPE-REDUCTION] Item 1 leaves pre-bootstrap invoke paths using empty ${CLAUDE_PLUGIN_ROOT}. Scenario: Wrapper self-derive runs only after the script is invoked; on initial Step 0 IMPLEMENT_TMPDIR and plugin-root.env are absent so lines 302-308 expand to /scripts/... and fail before the wrapper self-derive path runs
- **Proposed resolution**: Prefer the issue's cheaper alternative: one template-expanded export CLAUDE_PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-<plugin-root>}" at the top of each Step 0 fence (plus wrapper self-derive); drop post-invoke _inv_out parsing unless still needed after that

### FINDING_13:
- **Reviewer(s)**: Cursor-dyn-scope-control
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:42-59
- **Concern**: [SCOPE-REDUCTION] Step 0 parent-shell rehydration exceeds approved SKILL surface (outline limited changes to Step 5 banner). Scenario: Two new post-invoke blocks duplicate logic across initial and dirty-tree resume fences and expand acceptance beyond the approved outline surfaces
- **Proposed resolution**: Limit SKILL.md Item 1 to a single pre-invoke export line (or document explicit outline amendment); avoid dual-fence _inv_out KV scraping if the template export satisfies parent and child

### FINDING_14:
- **Reviewer(s)**: Cursor-dyn-scope-control
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:145-186
- **Concern**: [SCOPE-REDUCTION] Step 5 edit merges telemetry, dynamic_archetypes_cap derivation, validation, banner printf, and launcher—beyond Item 4's degraded-round CLI need. Scenario: ~40 lines of new fence bash reimplements banner math the issue scoped to prior_degraded_rounds; increases timing-rehydration and structure regression surface for cosmetic copy
- **Proposed resolution**: Keep the lib --count-prior-degraded CLI; either retain prompt-side dynamic_archetypes_cap with a minimal one-line banner fence, or add a narrow run-step5-review.sh --print-banner-values probe instead of inlining full cap precedence in SKILL.md

### FINDING_15:
- **Reviewer(s)**: Cursor-dyn-scope-control
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:145-186
- **Concern**: Proposed Step 5 merged fence adds : "${CLAUDE_PLUGIN_ROOT:?...}" guard not present in current Step 5 fences. Scenario: test-implement-timing-rehydration.sh pins exact plugin-root guard counts and tmpdir/telemetry coupling; a new loud guard plus deleted standalone telemetry fence can fail CI if counts drift
- **Proposed resolution**: Omit the new : guard (canonical plugin-root.env source is enough post-Step-0) or extend test-implement-timing-rehydration.sh in the same PR with updated pinned counts

### FINDING_16:
- **Reviewer(s)**: Codex-dyn-scope-control
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:298-318,364-388
- **Concern**: [SCOPE-REDUCTION] Proposed Step 0 parent-shell rehydration is outside the approved Step 0 surface and the inserted block is missing the outer fi. Scenario: The new Step 0 fence would parse as an unterminated if before routing-envelope parsing; even if fixed, it adds caller fallback behavior the approved outline excluded
- **Proposed resolution**: Remove the Step 0 SKILL.md insertion and keep item 1 to implement-bootstrap-invoke.sh self-derive/export only; if retained despite scope, add the missing fi before export

### FINDING_17:
- **Reviewer(s)**: Codex-dyn-scope-control
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:770-790; scripts/test-implement-timing-rehydration.sh:142-156
- **Concern**: [SCOPE-REDUCTION] Proposed Step 5 rewrite merges telemetry and review launch fences even though item 4 only needs replacing prompt-side banner derivation. Scenario: Deleting one existing plugin-root.env source guard drops the pinned guard count from 42 and makes make test-implement-timing-rehydration fail unless extra test churn is added
- **Proposed resolution**: Leave the telemetry fence at skills/implement/SKILL.md:770-775 intact; only replace the prompt-side banner prose and extend the existing run-step5-review fence to compute and print the banner via the new CLI before invoking run-step5-review.sh

### FINDING_18:
- **Reviewer(s)**: Cursor-dyn-shell-fence-flow
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:770-795 / scripts/test-implement-timing-rehydration.sh:154-156
- **Concern**: Step 5 merge deletes one of two identical `plugin-root.env` source guards; harness pins count at exactly 42. Scenario: Merged Step 5 fence keeps one guard while removing the standalone telemetry fence and the separate `run-step5-review` fence; `make test-implement-timing-rehydration` fails on `plugin_root_source_count ($plugin_root_source_count) expected 42`
- **Proposed resolution**: Add `scripts/test-implement-timing-rehydration.sh` to the plan (expected count 41, or document why 42 still holds); or retain a second guard line in the merged fence if the count must stay 42

### FINDING_19:
- **Reviewer(s)**: Cursor-dyn-shell-fence-flow
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:46-54
- **Concern**: Post-invoke block unconditionally `export CLAUDE_PLUGIN_ROOT` when the outer `if` is entered but `plugin-root.env` is missing or empty. Scenario: After a successful bootstrap with a missing/unreadable `plugin-root.env`, parent shell exports an empty `CLAUDE_PLUGIN_ROOT`; `. "${CLAUDE_PLUGIN_ROOT}/scripts/parse-bootstrap-routing-envelope.sh"` then fails opaquely
- **Proposed resolution**: Gate `export` on `[ -n "${CLAUDE_PLUGIN_ROOT:-}" ]` after sourcing, or abort with the same loud `:?` pattern used elsewhere in Step 0/Step 5 fences

### FINDING_20:
- **Reviewer(s)**: Codex-dyn-shell-fence-flow
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:311-318,380-388
- **Concern**: Step 0 parent rehydration snippet is syntactically incomplete. Scenario: The proposed insertion opens `if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ]; then` and closes only the inner plugin-root.env test; the fenced Step 0 initial and resume Bash blocks will hit a parse error before sourcing `parse-bootstrap-routing-envelope.sh`.
- **Proposed resolution**: Add the missing outer `fi` before `export CLAUDE_PLUGIN_ROOT` in both proposed insertions; keep `export CLAUDE_PLUGIN_ROOT` outside the guard.

### FINDING_21:
- **Reviewer(s)**: Codex-dyn-shell-fence-flow
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:115,770-795; scripts/test-implement-timing-rehydration.sh:154-156
- **Concern**: Step 5 fence merge changes the canonical plugin-root source-guard count without updating the pinned count/prose. Scenario: The plan deletes the standalone telemetry fence at current lines 770-775 and leaves one merged invocation fence, reducing canonical `plugin-root.env` source guards by one; `test-implement-timing-rehydration` still expects 42 and the Bash prelude still says 42 sites, so the stated test suite fails and stale docs remain.
- **Proposed resolution**: Add `scripts/test-implement-timing-rehydration.sh` and the Bash prelude count line to the plan, lowering the expected/source-site count to 41.

### FINDING_22:
- **Reviewer(s)**: Cursor-dyn-harness-wiring
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:199
- **Concern**: Makefile shard for test-append-execution-issue is unspecified. Scenario: Plan only says add to test-harnesses-N shard; scripts/test-harness-shards-coverage.sh requires exactly one shard prerequisite and .PHONY membership; CI fails until assigned
- **Proposed resolution**: Name the shard explicitly (e.g. test-harnesses-14 alongside test-append-tool-failure) in the Makefile ### UPDATED section

### FINDING_23:
- **Reviewer(s)**: Cursor-dyn-harness-wiring
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:161-165
- **Concern**: Step 5 banner dynamic_archetypes_cap precedence is inverted vs review-and-fix.sh. Scenario: Proposed fence reads session-env then ambient LARCH_DYNAMIC_ARCHETYPES_MAX; review-and-fix.sh resolves non-empty process env before session-env (skills/review-and-fix/scripts/review-and-fix.sh:1241-1259); Failure modes line 223 claims the opposite
- **Proposed resolution**: Reorder banner derivation to ambient env before session-env (or drop ambient and match run-step5-review.sh session-env-only forwarding)

### FINDING_24:
- **Reviewer(s)**: Cursor-dyn-harness-wiring
- **Severity**: nit
- **Focus area**: risk-integration
- **Location**: plan.txt:238-251
- **Concern**: docs/linting.md not listed for new harness. Scenario: scripts/test-harness-shards-coverage.md requires harness table updates when adding Makefile targets; omission leaves contributor docs stale
- **Proposed resolution**: Add test-append-execution-issue row to docs/linting.md in the same PR as the Makefile target

### FINDING_25:
- **Reviewer(s)**: Codex-dyn-harness-wiring
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:298-318,364-388; plan.txt:46-53
- **Concern**: Planned Step 0 parent rehydration snippet lacks the closing fi for the outer CLAUDE_PLUGIN_ROOT check. Scenario: Implementing the snippet literally leaves both Step 0 fences with an unterminated if, so Bash fails before parse-bootstrap-routing-envelope.sh runs
- **Proposed resolution**: Add the missing outer fi before export CLAUDE_PLUGIN_ROOT, leaving export outside the if so already-set values are exported too

### FINDING_26:
- **Reviewer(s)**: Codex-dyn-harness-wiring
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:770-790; scripts/test-implement-timing-rehydration.sh:153-156; scripts/test-implement-timing-rehydration.md:10-15
- **Concern**: Step 5 fence merge lowers the canonical plugin-root.env source-guard count but the plan does not update the hard-coded timing rehydration harness/docs. Scenario: After deleting the standalone Step 5 telemetry fence and keeping one merged guard, make test-implement-timing-rehydration still expects 42 guards and fails
- **Proposed resolution**: Update the expected plugin_root_source_count and sibling cardinality prose to the new count, or keep two guards if preserving 42 is intentional

### FINDING_27:
- **Reviewer(s)**: Cursor-dyn-contract-sync
- **Severity**: latent
- **Focus area**: architecture
- **Location**: Makefile:190-199 (plan § Makefile)
- **Concern**: `test-append-execution-issue` Makefile target is added but no concrete `test-harnesses-N` shard is named. Scenario: Implementer may omit shard wiring; `make test-harness-shards-coverage` will fail CI until fixed, but the plan gives no shard hint unlike nearby harness entries
- **Proposed resolution**: Name the target shard explicitly (e.g. `test-harnesses-14` alongside `test-append-tool-failure`) in the Makefile subsection

### FINDING_28:
- **Reviewer(s)**: Codex-dyn-contract-sync
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:298-318,364-388
- **Concern**: Proposed Step 0 parent rehydration block is missing the outer fi before export. Scenario: Applying the literal plan leaves the initial and resume fences with an unterminated if, so the Bash block fails to parse before parse-bootstrap-routing-envelope.sh
- **Proposed resolution**: Add the closing fi before export CLAUDE_PLUGIN_ROOT in both inserted blocks, or use a one-line guarded source form

### FINDING_29:
- **Reviewer(s)**: Codex-dyn-contract-sync
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:770-795; scripts/test-implement-timing-rehydration.sh:153-156
- **Concern**: Merged Step 5 fence reduces the canonical plugin-root source-guard count but the plan leaves the count-pinned harness out of scope. Scenario: Deleting the standalone Step 5 telemetry fence removes one exact plugin-root.env source line; test-implement-timing-rehydration still expects 42 and will fail after the proposed SKILL change
- **Proposed resolution**: Add scripts/test-implement-timing-rehydration.sh to the plan and update the expected count, and the SKILL prelude count if kept, to the final count after the merge likely 41
