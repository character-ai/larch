### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/implement/checks_lint_fix.py:435-504
- **Concern**: Step 3 lint-fix prompt still interleaves per-session submodule paths before static instruction blocks. Scenario: The plan only sorts `coder_delta_guards.submodule_paths`; `_compose_prompt` still emits the submodule prohibition between the intro and the Pyright/Ruff/final-line sections. When discovery yields a different path set or count, every static line after that block sits in the variable suffix, so `launch-claude-lint-fix` cannot reuse a long stable prefix across Step 3 repair attempts.
- **Proposed resolution**: Move the submodule prohibition block to immediately before the checks-log section (after all static instruction text), mirroring the specialist reorder: stable instructions first, session-varying submodule list and log tail last.

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/rendering/rendering.py:883-890
- **Concern**: Plan does not pin `competition_notice_file` body to the dynamic suffix. Scenario: The plan lists the competition notice among stable content but does not carve out the optional `--competition-notice-file` read. If that file content is folded into the stable prefix, per-session notice text invalidates cache for the large reviewer body that precedes it in the proposed layout.
- **Proposed resolution**: Keep only the static competition-notice prose in the stable chunk; append `_read_text(competition_notice_file)` in the dynamic suffix with the other per-session file blocks.

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: blocking
- **Focus area**: risk-integration
- **Location**: python/larch/rendering/rendering.py:864-870
- **Concern**: Comment rewrite drops the harness annotation token the plan requires. Scenario: The plan tells implementers to replace the `# intentionally non-stable:` comments with new wording, but `scripts/test-cache-key-discipline.sh` `has_nearby_annotation` and `check_render_specialist_prompt_paths` grep for that exact substring within three preceding lines. `make test-cache-key-discipline` will fail after the rendering edit unless the harness is updated in the same change.
- **Proposed resolution**: Either keep the literal `# intentionally non-stable:` prefix in the new comments, or add an explicit `### UPDATED: scripts/test-cache-key-discipline.sh` step to broaden `has_nearby_annotation` and document the new marker in `scripts/test-cache-key-discipline.md`.

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tests/rendering/test_rendering.py:324-361
- **Concern**: Planned ordering test omits ledger and checklist placement the plan treats as cache-critical. Scenario: The new `_render_specialist_text` test only checks body-before-preamble blocks. Today ledger sits between body and `_specialist_tagging` (rendering.py:880-882). The plan failure modes call out ledger-before-stable as a prefix-cache break, and it says to move ledger after the stable reviewer checklist. A partial reorder could pass the new test while leaving ledger ahead of tagging or competition text.
- **Proposed resolution**: Extend the planned test to assert stable sections (`_load_specialist_body` text, architectural guidelines when present, `_specialist_tagging`, competition notice) all precede `## Prior-round findings ledger`, and that the ledger precedes only the dynamic preamble or untrusted suffix blocks.

### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tests/rendering/test_rendering.py
- **Concern**: Planned ordering test omits findings-ledger placement. Scenario: The plan’s main Step 5 fix is moving per-round ledger content after the stable reviewer prefix, and failure modes warn that leaving ledger before stable sections still breaks prefix caching. The proposed test only checks body-before-diff/feature/plan ordering, so an implementation could reorder those blocks but leave `_code_ledger_section` ahead of `_specialist_tagging` / competition text (today’s layout) and still pass tests while multi-round review prompts keep rebuilding the shared tail.
- **Proposed resolution**: Extend the new `_render_specialist_text` test to render with a non-empty findings ledger and assert `Prior-round findings ledger` (or the ledger heading) appears after the loaded agent body and after `_specialist_tagging` output such as `### In-Scope Findings`, using `text.find` ordering rather than snapshots.

### FINDING_6:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tests/rendering/test_rendering.py
- **Concern**: Planned ordering test omits ledger placement after stable prefix. Scenario: The plan requires moving rendered ledger content after the stable prefix, but the proposed assertions only check that the reviewer body precedes diff/feature/plan blocks. An implementation could keep `_code_ledger_section` before the agent body while still satisfying those assertions (body before later diff lines), leaving per-round ledger bytes in the cache prefix and failing the issue goal for Step 5 `claude_sub` reviewers.
- **Proposed resolution**: Add assertions that the findings-ledger section appears after the stable reviewer body (and after specialist-tagging when present), not only that the body precedes diff/feature/plan blocks.

### FINDING_8:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/rendering/rendering.py
- **Concern**: Plan silent on final stable-prefix section order for guidelines vs tagging. Scenario: The plan says to move dynamic task preamble, feature/plan blocks, and ledger after the stable prefix, but does not pin whether `_architectural_guidelines_review_section`, specialist tagging, and competition notice stay in the stable prefix and in which order. Different orderings change the shared cacheable prefix across reviewers and can leave acceptance ambiguous.
- **Proposed resolution**: Spell out the target chunk order in the `rendering.py` section (e.g. agent body, then architectural guidelines, then specialist tagging/competition, then ledger, then diff/scope preamble and optional feature/plan blocks).

### FINDING_9:
- **Reviewer(s)**: Cursor-dyn-Cache Prefix Reviewer
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tests/rendering/test_rendering.py:811-879
- **Concern**: Planned specialist-ordering test omits ledger placement. Scenario: The plan requires moving rendered ledger content after the stable prefix (rendering.py failure modes), but the proposed test only asserts body-before-diff/feature/plan. An implementation could leave `## Prior-round findings ledger` before specialist body or tagging without failing CI.
- **Proposed resolution**: Extend the new `_render_specialist_text` test to assert `## Prior-round findings ledger` appears after the pre-rendered reviewer body and after diff/feature/plan path lines when a non-empty ledger is supplied.

### FINDING_10:
- **Reviewer(s)**: Cursor-dyn-Cache Prefix Reviewer
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/implement/checks_lint_fix.py:435-496
- **Concern**: Step 3 lint-fix prompt assembly is not reordered. Scenario: Step 3 `claude_sub` uses `_compose_prompt` via `launch-claude-lint-fix` (checks_lint_fix.py:1195-1214; _ci_launcher.py:976-981). The plan only sorts `submodule_paths` and adds harness scanning; it does not reorder this prompt. Per-run `fix_sentence`, submodule lists, and `target_cmd_display` still precede the large stable Pyright/Ruff/FIXED-contract blocks, so Step 3 prefix churn can remain even after rendering.py is fixed.
- **Proposed resolution**: Add an `### UPDATED: python/larch/implement/checks_lint_fix.py` step to move site-specific preamble, submodule prohibition, and checks-log path metadata after the stable instruction blocks, mirroring the rendering.py reorder (content unchanged, order only).

### FINDING_11:
- **Reviewer(s)**: Codex-dyn-Cache Prefix Reviewer
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/rendering/rendering.py:861-881
- **Concern**: _ren der_specialist_text still emits the per-run diff or description preamble and optional feature and plan blocks before the stable reviewer body.. Scenario: When `args.diff_file`, `args.description_text`, `args.scope_files`, `args.feature_file`, or `args.plan_file` changes, the earliest prompt bytes still change before the reviewer checklist, so the cacheable prefix is not actually stable and the plan's ordering contract is not met.
- **Proposed resolution**: Move the stable reviewer body and checklist ahead of the per-run preamble, then append the diff or description context and any optional feature or plan blocks after that stable prefix.

### FINDING_12:
- **Reviewer(s)**: Codex-dyn-Cache Prefix Reviewer
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/tests/rendering/test_rendering.py:823-879
- **Concern**: The specialist rendering tests do not assert the planned ordering contract for `_render_specialist_text`.. Scenario: A regression that puts the diff-file task line, feature block, or plan block back before the reviewer body can still pass the current content-only assertions, so the cache-prefix issue would ship unnoticed.
- **Proposed resolution**: Add the focused `_render_specialist_text` test the plan asked for, with diff, plan, and feature fixtures and index assertions that the reviewer body appears before each dynamic block.

### FINDING_13:
- **Reviewer(s)**: Codex-dyn-Cache Prefix Reviewer
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/core/coder_delta_guards.py:51-73
- **Concern**: `submodule_paths()` still returns discovery order instead of a sorted deterministic tuple.. Scenario: Two runs that discover the same submodules through different git outputs or filesystem orders can emit different forbidden-path ordering, which violates the plan's deterministic-order requirement and can ripple into later prompt or revert ordering.
- **Proposed resolution**: Return `tuple(sorted(paths))` after deduping, while keeping the existing unique-path collection intact.

### FINDING_14:
- **Reviewer(s)**: Codex-dyn-Cache Prefix Reviewer
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/tests/core/test_coder_delta_guards.py:9-53
- **Concern**: There is no test that exercises `submodule_paths()` with out-of-order and duplicate sources.. Scenario: The new sort-and-dedup contract can regress silently because the current tests only cover baseline change detection, prefix matching, revert behavior, and forbidden-path membership.
- **Proposed resolution**: Add the fake-runner temporary `.gitmodules` test from the plan and assert the returned tuple is sorted and unique.

### FINDING_15:
- **Reviewer(s)**: Codex-dyn-Cache Prefix Reviewer
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-cache-key-discipline.sh:95-179; scripts/test-cache-key-discipline.md:1-16
- **Concern**: The cache-key guard still only scans `python/larch/rendering/rendering.py`, `agents/*.md`, and `skills/implement/SKILL.md`; the four prompt-surface files named in the plan are absent from both the guard and its scope doc.. Scenario: New per-session prompt inputs in `python/larch/implement/checks_lint_fix.py`, `python/larch/review/coder_runner.py`, `python/larch/review/review_dispatch_panel.py`, and `python/larch/review/round_runner.py` can still introduce unstable prefix content without any guard coverage.
- **Proposed resolution**: Add the explicit file list to the shell check, fail when any listed file is missing, run the unstable-pattern scan over those files, and update the scope doc in the same PR.
