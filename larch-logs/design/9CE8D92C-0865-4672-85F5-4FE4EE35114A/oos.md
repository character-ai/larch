### FINDING_2: Specialist prompt stable prefix still needs a fixed order
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements, Codex-dyn-Cache Prefix Reviewer
- **Severity**: important
- **Concern**: `_render_specialist_text` still leaves some stable reviewer text and competition-related content mixed with per-run preamble/diff context, so the cacheable prefix and the intended stable-section order are not pinned down.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Keep only the static competition-notice prose in the stable chunk; append `_read_text(competition_notice_file)` in the dynamic suffix with the other per-session file blocks.
  - From Cursor-Requirements: Spell out the target chunk order in the `rendering.py` section (e.g. agent body, then architectural guidelines, then specialist tagging/competition, then ledger, then diff/scope preamble and optional feature/plan blocks).
  - From Codex-dyn-Cache Prefix Reviewer: Move the stable reviewer body and checklist ahead of the per-run preamble, then append the diff or description context and any optional feature or plan blocks after that stable prefix.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_5: `submodule_paths()` still depends on discovery order
- **Reviewer(s)**: Codex-dyn-Cache Prefix Reviewer
- **Severity**: important
- **Concern**: `submodule_paths()` still returns discovery order instead of a sorted deterministic tuple, so identical submodules can produce different forbidden-path ordering and the new contract is not covered by tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-Cache Prefix Reviewer: Return `tuple(sorted(paths))` after deduping, while keeping the existing unique-path collection intact.
  - From Codex-dyn-Cache Prefix Reviewer: Add the fake-runner temporary `.gitmodules` test from the plan and assert the returned tuple is sorted and unique.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_6: Cache-key guard misses new prompt-surface files
- **Reviewer(s)**: Codex-dyn-Cache Prefix Reviewer
- **Severity**: important
- **Concern**: `scripts/test-cache-key-discipline.sh` and its scope doc still omit the four prompt-surface files named in the plan, leaving new per-session prompt inputs unguarded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-Cache Prefix Reviewer: Add the explicit file list to the shell check, fail when any listed file is missing, run the unstable-pattern scan over those files, and update the scope doc in the same PR.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_1: [SCOPE-REDUCTION] Harness lists `round_runner.py` as a prompt-construction surface
- **Description**: [SCOPE-REDUCTION] Harness lists `round_runner.py` as a prompt-construction surface. Scenario: Round orchestration composes findings and env files; it does not assemble external-tool prompts or `claude_sub` prompt bodies. Adding it expands harness scope without guarding a Step 3/5 prefix path.
- **Reviewer**: Cursor-Arch
- **Severity**: nit
- **Focus area**: architecture
- **Location**: python/larch/review/round_runner.py:1-50
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_2: [SCOPE-REDUCTION] Harness adds a non-prompt file
- **Description**: [SCOPE-REDUCTION] Harness adds a non-prompt file. Scenario: `round_runner.py` orchestrates rounds and delegates prompt rendering to other modules; it does not assemble external-tool prompts. Scanning it adds harness surface without advancing Step 3 or Step 5 prefix stability.
- **Reviewer**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/review/round_runner.py:1-60
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_3: [OUT_OF_SCOPE] Harness lists round_runner.py as a prompt surface
- **Description**: [OUT_OF_SCOPE] Harness lists round_runner.py as a prompt surface. Scenario: `python/larch/review/round_runner.py` orchestrates round state and finding composition; it does not assemble external-tool prompts. Adding it to the cache-key file list expands harness scope without guarding a Step 3/5 instability source.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/test-cache-key-discipline.sh
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_4: [OUT_OF_SCOPE] Voter prompt assembly still interleaves dynamic ledger before ballot path
- **Description**: [OUT_OF_SCOPE] Voter prompt assembly still interleaves dynamic ledger before ballot path. Scenario: `render_voter_main` injects `_code_ledger_section` before the per-ballot `args.ballot_file` line, so growing ledgers can still invalidate the stable voting-instruction suffix on claude_sub voter calls in Step 5.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/rendering/rendering.py:1133-1200
- **Phase**: design




Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral

### OOS_5: Step 5 coder-fix prompt still embeds per-session paths mid-prompt
- **Description**: Step 5 coder-fix prompt still embeds per-session paths mid-prompt. Scenario: `_compose_coder_prompt` places `Read {findings_file}` and the session-directory line before the closing stable tail; that can reduce prefix reuse for `launch-claude-review-fix` `claude_sub` calls, but reviewer-volume `render specialist` fixes likely dominate Step 5 ratios and may satisfy acceptance without this change.
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/larch/review/coder_runner.py:356-380
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_6: round_runner.py listed without prompt construction
- **Description**: round_runner.py listed without prompt construction. Scenario: The harness expansion names `round_runner.py`, but the file only orchestrates review rounds and findings composition; it contains no prompt assembly strings or per-session path interpolation. Listing it adds maintenance surface without guarding prefix order.
- **Reviewer**: Cursor-dyn-Cache Prefix Reviewer
- **Severity**: nit
- **Focus area**: architecture
- **Location**: python/larch/review/round_runner.py:1-683
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

