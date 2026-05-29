### FINDING_1: Context files outside granted read roots
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Edge, Codex-Edge, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: Path-only scout prompts can reference validated context files (plan, feature description, etc.) whose paths pass `validate_context_input_file` under broader allowed roots (`PLUGIN_ROOT`, caller session root, `IMPLEMENT_TMPDIR`, `dirname("$SESSION_ENV_PATH")`) than the directories actually granted to launched agents. Claude/Codex/Cursor tiers are only given the scout output dir and/or `SESSION_ROOT` via `--add-dir` / `--read-tools`, while callers routinely place context under sibling tmpdirs (e.g. `/design` with `feature-description.txt` in `IMPLEMENT_TMPDIR` and scout output in `DESIGN_TMPDIR`; `/implement` Step 5 with `plan.txt` in parent `IMPLEMENT_TMPDIR` and round output under `round-N/`). Agents cannot Read those paths, and the scout fail-opens to zero dynamic archetypes—often with no hard error—on paths the plan and harnesses (e.g. `test-dispatch-panel.sh` with `--plan-file` in `design-export/` and `--review-tmpdir` in `round-1/`) are meant to exercise.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Codex-Arch: Before writing the prompt, copy each validated context file into SESSION_ROOT and reference those copied paths, or pass every validated context root as an add-dir/read root to all three tiers. Add a harness case where a context file is valid but outside SESSION_ROOT.
  - From Cursor-Edge: When building the waterfall, collect the parent directory of each canonical context path and pass `--allow-root` (and any needed `--add-dir`) for every distinct root, mirroring `scripts/launch-claude-review.sh:139-142`; or stage/symlink all context files under `SESSION_ROOT` and reference those paths in the prompt
  - From Codex-Edge: Copy every validated context input into SESSION_ROOT and prompt those copied paths, or grant each validated context root to every launcher tier before removing embedding
  - From Cursor-Innovation: Mirror launch-claude-review.sh append_context_file: pass one --allow-root per distinct parent dir of each referenced context file to the Claude tier, and extend Codex/Cursor launch (extra --add-dir or pre-copy/symlink into the output dir) before dropping embed
  - From Cursor-Pragmatic, Codex-Pragmatic: Make the paths in the generated scout prompt readable by every tier: either stage validated context files under $SESSION_ROOT and reference those staged paths, or pass every validated context directory as an added read directory to Codex, Cursor, and Claude.
  - From Codex-Requirements: Add the validated context-file parent roots to the read-capable launch for every tier, or copy/context-stage those files into SESSION_ROOT before prompting and test a plan file outside the output dir


### FINDING_2: Cursor tier cannot read scout output / session tmpdir paths
- **Reviewer(s)**: Codex-Innovation, Cursor-dyn-launcher-contract
- **Severity**: important
- **Concern**: The planned Codex→Cursor→Claude scout waterfall assumes Cursor can read prompt-referenced files under the scout session tmpdir (e.g. `$REVIEW_TMPDIR/diff.txt`, scope, plan paths) via `launch-review.sh`, but the Cursor launcher only sets `--workspace "$PWD"` and has no `--add-dir` or equivalent out-of-workspace read grant for `CANON_OUTPUT_DIR`. Codex may get `--add-dir` on the output dir while Cursor’s workspace is repo CWD and context lives under `/tmp` (or similar). When Codex is unavailable or fails, Cursor can return a valid empty archetype manifest because it cannot read those files; that result can win the waterfall and prevent Claude from running, or the tier fails JSON parse and falls through without exercising real multi-tier behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Either add and test a Cursor read-root mechanism for the scout output directory, or keep SIMPLE by dropping Cursor from this scout waterfall until that support exists.
  - From Cursor-dyn-launcher-contract: Drop the Cursor tier for scout unless launch-review gains a supported out-of-workspace read grant, or document Cursor as non-viable and skip it in the waterfall (Codex then Claude only)


### FINDING_3: `test-gather-branch-context.sh` not registered in Makefile CI
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The plan adds a new `scripts/test-gather-branch-context.sh` harness but does not register it in Makefile CI shards. Only `test-gather-context` is wired (`Makefile` `test-harnesses-8`). A new harness would not run under `make lint` unless a target and shard entry are added, so the larch-logs pathspec exclusion could ship without automated regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add a Makefile test-gather-branch-context target (harness-timer wrapper) and attach it to an appropriate test-harnesses-N shard in the same change, or fold the include/exclude assertions into an existing registered harness instead of a standalone unregistered file.


### FINDING_4: SECURITY.md not updated for `--read-tools` trust boundary
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The plan changes Claude subprocess trust boundaries (`--read-tools`, allowed tool surface, read roots) but does not update `SECURITY.md`. `AGENTS.md` requires `SECURITY.md` updates for security-relevant behavior changes; the documented prompt-only read-only model and permission/read-root behavior would be stale.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Update SECURITY.md in the plan to document --read-tools, allowedTools, permission-mode choice, and the exact read-root behavior


### FINDING_5: No test coverage for presence-flag forwarding across caller hops
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: Presence-flag forwarding (`--codex-present` / `--cursor-present`) is planned for callers, but listed tests do not cover the two-hop path through `dispatch-panel.sh` and `plan-review-loop.sh`. A regression could silently leave `/implement` or `/design` on Claude-only scouting despite Codex/Cursor being available.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add minimal stub assertions in test-dispatch-panel.sh and test-plan-review-loop.sh that --codex-present/--cursor-present reach their scout child


### FINDING_6: Missing `test-gather-branch-context.md` script-md sibling
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: If the plan creates `scripts/test-gather-branch-context.sh` without the required sibling `scripts/test-gather-branch-context.md` contract, script-md-sibling lint fails because the `.md` file is not listed in the planned file set.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add scripts/test-gather-branch-context.md to the planned file set when creating the harness, or explicitly state that an existing harness path will be extended instead


### FINDING_7: `SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_SH` overrides all tiers, not only Claude
- **Reviewer(s)**: Cursor-dyn-env-threading
- **Severity**: important
- **Concern**: `SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_SH` is bound once at startup to `LAUNCH_CLAUDE_SUBPROCESS_SH` for the launch path. The plan adds a Codex/Cursor/Claude waterfall but only says the override applies to the Claude tier while testing ties tier selection to the same env var. A refactor that keeps calling `$LAUNCH_CLAUDE_SUBPROCESS_SH` for every tier—or tests that only stub that var—will skip real `launch-review.sh` Codex/Cursor launches when the var is set (e.g. `test-dispatch-panel.sh`, `test-scout-dynamic-archetypes.sh`), so `--codex-present true` never exercises external tiers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-env-threading: In the waterfall helper, call `scripts/launch-review.sh` directly for Codex/Cursor; use `SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_SH` only on the Claude `--read-tools` branch. Extend `scripts/test-scout-dynamic-archetypes.sh` with a separate `launch-review.sh` stub (PATH or dedicated env) for external-tier assertions; reserve `SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_SH` for Claude-only cases. Clarify plan.txt:37 accordingly.


### FINDING_8: `plan-review-loop.sh` does not forward presence flags to scout
- **Reviewer(s)**: Cursor-dyn-env-threading
- **Severity**: important
- **Concern**: The plan says `plan-review-loop` forwards presence into the scout wrapper, but the proposed caller change is not spelled out at the `PLAN_REVIEW_SCOUT_SH` invocation (panel dispatch elsewhere already passes `--codex-present` / `--cursor-present`). Implementing only wrapper flag parsing without adding those flags to the scout call leaves `/design` plan-review on Claude-only scout despite `CODEX_PRESENT` / `CURSOR_PRESENT` on the loop argv.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-env-threading: Add those two flags to the `"$PLAN_REVIEW_SCOUT_SH"` invocation in `plan-review-loop.sh` and assert forwarding in `skills/design/scripts/test-plan-review-loop.sh` / `test-scout-plan-archetypes-wrapper.sh`.

