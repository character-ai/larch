### FINDING_1: Step 3 prompt order still leaks session-varying paths
- **Reviewer(s)**: Cursor-Arch, Cursor-dyn-Cache Prefix Reviewer
- **Severity**: important
- **Concern**: `checks_lint_fix.py` still places session-varying preamble/submodule metadata ahead of the stable instruction blocks, so the Step 3 `claude_sub` prompt cannot keep a reusable cacheable prefix across repair attempts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Move the submodule prohibition block to immediately before the checks-log section (after all static instruction text), mirroring the specialist reorder: stable instructions first, session-varying submodule list and log tail last.
  - From Cursor-dyn-Cache Prefix Reviewer: Add an `### UPDATED: python/larch/implement/checks_lint_fix.py` step to move site-specific preamble, submodule prohibition, and checks-log path metadata after the stable instruction blocks, mirroring the rendering.py reorder (content unchanged, order only).

### FINDING_2: Specialist prompt stable prefix still needs a fixed order
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements, Codex-dyn-Cache Prefix Reviewer
- **Severity**: important
- **Concern**: `_render_specialist_text` still leaves some stable reviewer text and competition-related content mixed with per-run preamble/diff context, so the cacheable prefix and the intended stable-section order are not pinned down.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Keep only the static competition-notice prose in the stable chunk; append `_read_text(competition_notice_file)` in the dynamic suffix with the other per-session file blocks.
  - From Cursor-Requirements: Spell out the target chunk order in the `rendering.py` section (e.g. agent body, then architectural guidelines, then specialist tagging/competition, then ledger, then diff/scope preamble and optional feature/plan blocks).
  - From Codex-dyn-Cache Prefix Reviewer: Move the stable reviewer body and checklist ahead of the per-run preamble, then append the diff or description context and any optional feature or plan blocks after that stable prefix.

### FINDING_3: Specialist rendering tests still miss the ledger ordering contract
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Cache Prefix Reviewer, Codex-dyn-Cache Prefix Reviewer
- **Severity**: important
- **Concern**: The planned `_render_specialist_text` coverage does not fully assert ledger placement relative to the stable reviewer body and specialist-tagging output, so a partial reorder could still pass while cache-prefix churn remains.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Extend the planned test to assert stable sections (`_load_specialist_body` text, architectural guidelines when present, `_specialist_tagging`, competition notice) all precede `## Prior-round findings ledger`, and that the ledger precedes only the dynamic preamble or untrusted suffix blocks.
  - From Cursor-Pragmatic: Extend the new `_render_specialist_text` test to render with a non-empty findings ledger and assert `Prior-round findings ledger` (or the ledger heading) appears after the loaded agent body and after `_specialist_tagging` output such as `### In-Scope Findings`, using `text.find` ordering rather than snapshots.
  - From Cursor-Requirements: Add assertions that the findings-ledger section appears after the stable reviewer body (and after specialist-tagging when present), not only that the body precedes diff/feature/plan blocks.
  - From Cursor-dyn-Cache Prefix Reviewer: Extend the new `_render_specialist_text` test to assert `## Prior-round findings ledger` appears after the pre-rendered reviewer body and after diff/feature/plan path lines when a non-empty ledger is supplied.
  - From Codex-dyn-Cache Prefix Reviewer: Add the focused `_render_specialist_text` test the plan asked for, with diff, plan, and feature fixtures and index assertions that the reviewer body appears before each dynamic block.

### FINDING_4: Harness annotation token rewrite will break cache-key discipline checks
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: blocking
- **Concern**: The comment rewrite drops the exact harness annotation token that `scripts/test-cache-key-discipline.sh` looks for, so the cache-key discipline check will fail unless the harness changes in the same patch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Either keep the literal `# intentionally non-stable:` prefix in the new comments, or add an explicit `### UPDATED: scripts/test-cache-key-discipline.sh` step to broaden `has_nearby_annotation` and document the new marker in `scripts/test-cache-key-discipline.md`.

### FINDING_5: `submodule_paths()` still depends on discovery order
- **Reviewer(s)**: Codex-dyn-Cache Prefix Reviewer
- **Severity**: important
- **Concern**: `submodule_paths()` still returns discovery order instead of a sorted deterministic tuple, so identical submodules can produce different forbidden-path ordering and the new contract is not covered by tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-Cache Prefix Reviewer: Return `tuple(sorted(paths))` after deduping, while keeping the existing unique-path collection intact.
  - From Codex-dyn-Cache Prefix Reviewer: Add the fake-runner temporary `.gitmodules` test from the plan and assert the returned tuple is sorted and unique.

### FINDING_6: Cache-key guard misses new prompt-surface files
- **Reviewer(s)**: Codex-dyn-Cache Prefix Reviewer
- **Severity**: important
- **Concern**: `scripts/test-cache-key-discipline.sh` and its scope doc still omit the four prompt-surface files named in the plan, leaving new per-session prompt inputs unguarded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-Cache Prefix Reviewer: Add the explicit file list to the shell check, fail when any listed file is missing, run the unstable-pattern scan over those files, and update the scope doc in the same PR.

### FINDING_7:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-cache-key-discipline.sh
- **Concern**: [SCOPE-REDUCTION] `round_runner.py` listed without prompt construction. Scenario: `python/larch/review/round_runner.py` orchestrates review rounds and delegates prompt work to `review_pipeline` / `coder_runner`; it contains no prompt assembly. Adding it to the cache-key guard expands harness scope without protecting a Step 3/5 `claude_sub` surface and adds maintenance noise.
- **Proposed resolution**: Drop `python/larch/review/round_runner.py` from the explicit prompt-surface file list; keep the three files that actually assemble or dispatch prompts (`checks_lint_fix.py`, `coder_runner.py`, `review_dispatch_panel.py`).
