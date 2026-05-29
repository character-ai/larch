### FINDING_1:
- **Reviewer(s)**: Cursor-Arch, Codex-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/scout-dynamic-archetypes.sh:97-123
- **Concern**: Proposed path-only prompt can reference validated context files outside the directory granted to the launched agents. Scenario: The plan keeps allowed context roots broader than the launched read root: PLUGIN_ROOT, caller session root, and IMPLEMENT_TMPDIR are accepted, but Codex/Cursor only get the scout output dir via launch-review and Claude read-tools only gets SESSION_ROOT. In /design, plan-review-loop can pass feature-description.txt from IMPLEMENT_TMPDIR while the scout output is in DESIGN_TMPDIR, so every tier may be unable to Read the description and fail open to no dynamic archetypes.
- **Proposed resolution**: Before writing the prompt, copy each validated context file into SESSION_ROOT and reference those copied paths, or pass every validated context root as an add-dir/read root to all three tiers. Add a harness case where a context file is valid but outside SESSION_ROOT.

### FINDING_2:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/scout-dynamic-archetypes.sh:97-125; scripts/launch-claude-subprocess.sh:94-123; skills/review/scripts/test-dispatch-panel.sh:500-517
- **Concern**: Tool reads are only granted under the scout output dir, but validated context files may live in other allowed roots. Scenario: `validate_context_input_file` allows paths under `dirname("$SESSION_ENV_PATH")` and `IMPLEMENT_TMPDIR`, while the plan only adds `--add-dir "$SESSION_ROOT"` (Claude) or `launch-review.sh`'s output-dir `--add-dir` (Codex/Cursor). The dispatch-panel harness already uses `--plan-file` in `design-export/` with `--review-tmpdir` in `round-1/`; agents cannot Read that plan and the scout fail-opens to zero archetypes with no hard error
- **Proposed resolution**: When building the waterfall, collect the parent directory of each canonical context path and pass `--allow-root` (and any needed `--add-dir`) for every distinct root, mirroring `scripts/launch-claude-review.sh:139-142`; or stage/symlink all context files under `SESSION_ROOT` and reference those paths in the prompt

### FINDING_3:
- **Reviewer(s)**: Codex-Edge
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/scout-dynamic-archetypes.sh:217-230
- **Concern**: Proposed path-only prompts can name context files outside the launcher-readable root. Scenario: /implement Step 5 runs review rounds under $IMPLEMENT_TMPDIR/round-N while plan.txt and feature-description.txt live in the parent $IMPLEMENT_TMPDIR; the plan says Claude/Codex/Cursor will only add the scout output dir/session root, and launch-review --prompt-file does not otherwise grant or embed those --plan-file paths, so tiers may fail or silently scout without plan context
- **Proposed resolution**: Copy every validated context input into SESSION_ROOT and prompt those copied paths, or grant each validated context root to every launcher tier before removing embedding

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/scout-dynamic-archetypes.sh:18-22,297-307
- **Concern**: Tool reads only grant SESSION_ROOT (--add-dir / --read-tools) but validated context files can live under IMPLEMENT_TMPDIR or other allowed roots outside dirname(OUTPUT). Scenario: Implement /review passes --plan-file "$IMPLEMENT_TMPDIR/plan.txt" while scout output lives under REVIEW_TMPDIR; path-only prompts tell the agent to Read paths the launcher cannot access, yielding empty archetypes after all tiers
- **Proposed resolution**: Mirror launch-claude-review.sh append_context_file: pass one --allow-root per distinct parent dir of each referenced context file to the Claude tier, and extend Codex/Cursor launch (extra --add-dir or pre-copy/symlink into the output dir) before dropping embed

### FINDING_5:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/launch-review.sh:928-933
- **Concern**: Cursor scout tier is planned to read diff paths through launch-review.sh, but the Cursor launcher only sets --workspace "$PWD" and has no extra read root for the scout output directory.. Scenario: When Codex is unavailable or fails, Cursor can return a valid empty archetype manifest because it cannot read "$REVIEW_TMPDIR/diff.txt"; that valid empty result wins the waterfall and prevents Claude from running.
- **Proposed resolution**: Either add and test a Cursor read-root mechanism for the scout output directory, or keep SIMPLE by dropping Cursor from this scout waterfall until that support exists.

### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/scout-dynamic-archetypes.sh:97-123, scripts/launch-claude-subprocess.sh:147-165, skills/design/SKILL.md:1040-1044
- **Concern**: Read-tool tiers only grant the scout output directory, but validated scout inputs may live under IMPLEMENT_TMPDIR or caller session roots. Scenario: /design passes --feature-file ${IMPLEMENT_TMPDIR:-$DESIGN_TMPDIR}/feature-description.txt while the scout output remains under DESIGN_TMPDIR; after prompt embedding is removed, tiers are told to read a path outside the only added tool directory and can fail open to zero archetypes on exactly the /design path the plan says to support
- **Proposed resolution**: Make the paths in the generated scout prompt readable by every tier: either stage validated context files under $SESSION_ROOT and reference those staged paths, or pass every validated context directory as an added read directory to Codex, Cursor, and Claude.

### FINDING_7:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-gather-branch-context.sh; Makefile
- **Concern**: Plan adds a new gather-branch-context harness but does not register it in Makefile CI shards. Scenario: The plan says create or extend scripts/test-gather-branch-context.sh and run relevant-checks.sh, but only test-gather-context is wired (Makefile test-harnesses-8). A new scripts/test-gather-branch-context.sh would not run under make lint unless a target and shard entry are added, so the larch-logs pathspec exclusion could ship without automated regression.
- **Proposed resolution**: Add a Makefile test-gather-branch-context target (harness-timer wrapper) and attach it to an appropriate test-harnesses-N shard in the same change, or fold the include/exclude assertions into an existing registered harness instead of a standalone unregistered file.

### FINDING_8:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/run-step5-review.sh:163-195; scripts/launch-review.sh:503-520
- **Concern**: The plan grants tool reads only to the scout output directory, but Step 5 passes the plan from the parent IMPLEMENT_TMPDIR. Scenario: With prompt-embedding removed, Codex/Cursor/Claude scout tiers can be asked to Read $IMPLEMENT_TMPDIR/plan.txt while only the round output dir is added, so the plan context may be unreadable in the main /implement review path
- **Proposed resolution**: Add the validated context-file parent roots to the read-capable launch for every tier, or copy/context-stage those files into SESSION_ROOT before prompting and test a plan file outside the output dir

### FINDING_9:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md:111
- **Concern**: The plan changes Claude subprocess trust boundaries but does not update SECURITY.md. Scenario: AGENTS.md requires SECURITY.md updates for security-relevant behavior changes, and --read-tools changes the documented prompt-only read-only model, allowed tool surface, and read roots
- **Proposed resolution**: Update SECURITY.md in the plan to document --read-tools, allowedTools, permission-mode choice, and the exact read-root behavior

### FINDING_10:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/scripts/test-dispatch-panel.sh; skills/design/scripts/test-plan-review-loop.sh
- **Concern**: Presence-flag forwarding is planned for callers but the listed tests do not cover two caller hops. Scenario: A regression in dispatch-panel.sh or plan-review-loop.sh would silently leave /implement or /design on Claude-only scouting despite Codex/Cursor being available
- **Proposed resolution**: Add minimal stub assertions in test-dispatch-panel.sh and test-plan-review-loop.sh that --codex-present/--cursor-present reach their scout child

### FINDING_11:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: code-quality
- **Location**: scripts/test-gather-branch-context.sh; scripts/test-gather-branch-context.md
- **Concern**: The plan may create a new test script without its required sibling md contract. Scenario: If scripts/test-gather-branch-context.sh is absent and added as planned, script-md-sibling lint fails because scripts/test-gather-branch-context.md is not listed
- **Proposed resolution**: Add scripts/test-gather-branch-context.md to the planned file set when creating the harness, or explicitly state that an existing harness path will be extended instead

### FINDING_12:
- **Reviewer(s)**: Cursor-dyn-launcher-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/launch-review.sh:502-504,928-933
- **Concern**: Plan claims Codex/Cursor scout tiers read context via launch-review --add-dir over the output dir; Cursor argv has no --add-dir and uses --workspace "$PWD" only. Scenario: Codex gets --add-dir on CANON_OUTPUT_DIR (session tmpdir) so path-based reads can work; Cursor workspace is repo CWD while diff/scope/plan paths live under session tmpdir (often /tmp), so the Cursor tier cannot Read prompt-referenced files and will usually fail JSON parse then fall through
- **Proposed resolution**: Drop the Cursor tier for scout unless launch-review gains a supported out-of-workspace read grant, or document Cursor as non-viable and skip it in the waterfall (Codex then Claude only)

### FINDING_13:
- **Reviewer(s)**: Cursor-dyn-env-threading
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/scout-dynamic-archetypes.sh:26
- **Concern**: `SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_SH` is bound once at startup as `LAUNCH_CLAUDE_SUBPROCESS_SH` for the only launch path; the plan adds a Codex/Cursor/Claude waterfall but only says the override applies to the Claude tier (plan.txt:16-17) while the testing bullet ties tier selection to that same env var (plan.txt:37).. Scenario: A waterfall refactor that keeps calling `$LAUNCH_CLAUDE_SUBPROCESS_SH` for every tier, or tests that only stub that env var, will skip real `launch-review.sh` Codex/Cursor launches whenever the var is set (e.g. `skills/review/scripts/test-dispatch-panel.sh` and `scripts/test-scout-dynamic-archetypes.sh`), so `--codex-present true` still never exercises the external tiers.
- **Proposed resolution**: In the waterfall helper, call `scripts/launch-review.sh` directly for Codex/Cursor; use `SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_SH` only on the Claude `--read-tools` branch. Extend `scripts/test-scout-dynamic-archetypes.sh` with a separate `launch-review.sh` stub (PATH or dedicated env) for external-tier assertions; reserve `SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_SH` for Claude-only cases. Clarify plan.txt:37 accordingly.

### FINDING_14:
- **Reviewer(s)**: Cursor-dyn-env-threading
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:666-671
- **Concern**: The plan says plan-review-loop forwards presence into the scout wrapper, but the proposed caller change is not spelled out at the only scout invocation; panel dispatch at 674-677 already passes `--codex-present` / `--cursor-present`.. Scenario: Implementing only `scout-plan-archetypes-wrapper.sh` flag parsing without adding `--codex-present "$CODEX_PRESENT" --cursor-present "$CURSOR_PRESENT"` to the `PLAN_REVIEW_SCOUT_SH` call leaves `/design` plan-review on Claude-only scout despite `CODEX_PRESENT`/`CURSOR_PRESENT` on the loop argv.
- **Proposed resolution**: Add those two flags to the `"$PLAN_REVIEW_SCOUT_SH"` invocation in `plan-review-loop.sh` and assert forwarding in `skills/design/scripts/test-plan-review-loop.sh` / `test-scout-plan-archetypes-wrapper.sh`.
