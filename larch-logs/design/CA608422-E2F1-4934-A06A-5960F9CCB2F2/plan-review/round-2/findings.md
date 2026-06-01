### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: SECURITY.md:105
- **Concern**: Step 0 paragraph still frames Cursor-first reversal and tells operators to pin --coder=codex for Codex default. Scenario: After #3337 Codex is the omitted---coder default; unchanged text misstates product direction and tells operators to pin the tool they already get by default
- **Proposed resolution**: In the ~105 edit, replace Cursor-first reversal wording with Codex-first (#3337), update the availability arrow to Codex then Cursor then Claude, and invert pin guidance (e.g. operators who want Cursor pin --coder=cursor); keep explicit-pin fail-closed sentences

### FINDING_2:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_ci_monitor.py:493-551,554-606,874-903,953-976
- **Concern**: Plan limits Python test updates to test_config.py (and optionally test_agents.py / test_rebase.py) but FIXER_TIER_ORDER drives ci_monitor.run_ci_fix / evaluate_failure / monitor. Scenario: After config.py flips to codex-first, tests that assert launch_calls == ["cursor"], mock only Apply CI fixes (cursor), or assume start_attempt=0 hits Cursor will fail under full make py-test even though the narrowed pytest list in the plan may pass
- **Proposed resolution**: Add python/test_ci_monitor.py to the plan: retarget tier-order assertions and commit-script mocks to codex-first (and rotation attempt 0/1 comments); run make py-test in Testing strategy

### FINDING_3:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: docs/linting.md:272;scripts/implement-bootstrap.md:169
- **Concern**: implement-bootstrap.md edit-in-sync requires docs/linting.md for Step 0 wording; plan updates bootstrap.md but not linting.md. Scenario: Makefile harness table still documents omitted--coder as Cursor → Codex → Claude after Part 2 lands; operators and contributors get wrong routing contract without CI failure
- **Proposed resolution**: Extend Part 2 doc sync to docs/linting.md (line ~272) per bootstrap.md:169; add docs/linting.md to the post-edit grep list in Failure modes

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ship-pr.md:72,118,154
- **Concern**: Plan lists arrow-order edits but not first-fixer tier-name literals tied to cursor-first. Scenario: After codex-first flip, docs still say the Cursor CI-fix launcher / first tier (cursor) triggers first-fixer-non-health; operators misread which vendor bailed and Step 8+ prose disagrees with ship-pr.sh
- **Proposed resolution**: Add explicit ship-pr.md edits: line 72 Codex (or first-tier) CI-fix launcher; line 118 first tier (codex) and codex→cursor→claude launch order; line 154 drop literal cursor tier (first tier of rotated list)

### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:1169
- **Concern**: Plan only rewrites the Step 0 `phase_coder_select` paragraph (~511); Exit 3 still says `first-fixer-non-health` fires when the Cursor CI-fix launcher reports `LAUNCHER_FAILURE_CLASS=other`. Scenario: After codex-first `run_ci_fix_vendor`, the bail keys on the rotated first tier (`first_tier` from `start_attempt % 3`), which is Codex on attempt 0 — not Cursor-only. Operators can mis-debug Exit 3 / autonomous CI-fix as a Cursor-only path
- **Proposed resolution**: Add a `skills/implement/SKILL.md` doc-sync step for ~1169: describe first-tier / rotated-first-tier CI-fix launcher (match `scripts/ship-pr.md:154`), not Cursor by name

### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ship-pr.md:72
- **Concern**: `ship-pr.md` sync is scoped to waterfall-order lines (~118–129, ~152) but line 72 still hardcodes Cursor for `first-fixer-non-health`. Scenario: Same drift as SKILL.md:72 — exit-3 contract text disagrees with codex-first base order and rotation-aware `first_tier`
- **Proposed resolution**: Extend the `ship-pr.md` grep/sync pass to line 72 (and any similar first-fixer sentences): first-tier launcher wording, not Cursor-only

### FINDING_7:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_ci_monitor.py:551,509-514,569-572,900-902
- **Concern**: Plan updates only python/test_config.py for FIXER_TIER_ORDER but make py-test runs full pytest. Scenario: After config.FIXER_TIER_ORDER flips, start_attempt=0 invokes codex first; test_run_ci_fix_pushed_after_winning_tier asserts launch_calls == ["cursor"] and stubs only Apply CI fixes (cursor); first-fixer/commit paths that stub cursor-only commits can fail under codex-first
- **Proposed resolution**: Add ### UPDATED: python/test_ci_monitor.py: retarget cursor-first assertions/stubs/comments (e.g. launch_calls == ["codex"], codex commit-msg keys, line 900 rotation comment) and list the file in Testing strategy alongside test_config.py
