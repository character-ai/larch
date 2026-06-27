### OOS_1: [OUT_OF_SCOPE] dialectic-legacy.md Consumer Contract markdown formatting
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: important
- **Concern**: In `skills/design/references/dialectic-legacy.md:307-308`, the moved Consumer Contract Step 2b/3.5 list item runs directly into the following paragraph with no blank line, so markdown may render it as one list item. Pre-existing formatting preserved by the move; not introduced by the split logic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Insert a blank line before "The artifact uses the basename…".

### OOS_2: [OUT_OF_SCOPE] disposition enum doc/runtime gap (pre-existing)
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: important
- **Concern**: The active disposition enum documents four labels, but `python/design_dialectic.py` only assigns `voted` and `fallback-to-synthesis`. `bucket-skipped` / `over-cap` clarifier meanings are doc-only today. Pre-existing doc/runtime drift; plan required keeping all four in the active file for clarifier binding and this PR does not change Python behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Either emit those labels when Gate C skips/caps candidates, or narrow the active enum to labels the clarifier actually produces.

### OOS_3: [OUT_OF_SCOPE] progress-reporting nested dispatch discoverability
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: important
- **Concern**: Nested `--step-prefix` parsing now lives only in `step-prefix-encoding.md`. Standalone skills that load `progress-reporting.md` but skip the pointer on nested dispatch could mis-format step numbers or skill paths. Out of scope for this PR; pointers in progress-reporting are adequate if agents follow them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Add an explicit "when nesting, also load `step-prefix-encoding.md`" rule in a future orchestrator SKILL edit (out of scope for this PR). Pointers here are adequate if agents follow them.

### OOS_4: [OUT_OF_SCOPE] plan verification greps not encoded in CI
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: important
- **Concern**: The plan lists many manual `rg` checks (legacy-label bans, retained-core positives, voter-scaffolding negatives) but none are encoded in `scripts/test-*.sh`. `make lint` can stay green if someone reintroduces retired Step 2a.5 prose into the active dialectic file or duplicate `--step-prefix` encoding back into `progress-reporting.md`. Plan scoped those greps as operator-run verification, not CI artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Encode the plan's manual `rg` verification checks in `scripts/test-*.sh` so retired prose reintroduction is caught by CI.

### OOS_5: [OUT_OF_SCOPE] step-prefix-encoding.md lacks header harness coverage
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: important
- **Concern**: `skills/shared/step-prefix-encoding.md:1-7` uses the Consumer/Contract/When-to-load triplet, but `test-references-headers.sh` only scans `skills/*/references/*.md`, so this shared sub-reference has no mechanical header enforcement. Plan did not extend the harness glob.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Extend `test-references-headers.sh` glob to cover `skills/shared/step-prefix-encoding.md`.

### OOS_6: [OUT_OF_SCOPE] dialectic-legacy.md Consumer Contract path inconsistency
- **Reviewer(s)**: dyn-dyn-reference-split
- **Severity**: important
- **Concern**: The parked Consumer Contract in `skills/design/references/dialectic-legacy.md:305-308` still mixes `$DESIGN_TMPDIR/dialectic-resolutions.md` with "under `$DIALECTIC_TMPDIR`" in adjacent bullets. Pre-existing inconsistency carried over from pre-split source; plan explicitly preserved legacy dangling references rather than fixing them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-reference-split: Harmonize `$DESIGN_TMPDIR` vs `$DIALECTIC_TMPDIR` references in the legacy Consumer Contract block.

### OOS_7: [OUT_OF_SCOPE] conflict-resolution references retired run-external-agent.sh
- **Reviewer(s)**: dyn-dyn-dispatch-docs
- **Severity**: important
- **Concern**: Pre-existing: `skills/implement/references/conflict-resolution.md:87-88` references `run-external-agent.sh`, which no longer exists in the repo. This branch did not introduce that stale binding; it only removed the shared argv fallback that partially compensated for it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-dispatch-docs: Repoint conflict-resolution voter launch to `python/cli.py agent run-external-agent` (or equivalent current Python surface).

### OOS_8: [OUT_OF_SCOPE] conflict-resolution voter panel composition mismatch
- **Reviewer(s)**: dyn-dyn-dispatch-docs
- **Severity**: important
- **Concern**: Pre-existing / out of plan scope: `skills/implement/references/conflict-resolution.md:85-88` uses a 3-voter composition (Claude + Codex + Cursor) that diverges from the fixed code-review panel documented in `skills/shared/voting-protocol.md:66-71`. That mismatch predates this documentation split.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-dispatch-docs: Align conflict-resolution voter composition with the fixed code-review panel in `voting-protocol.md`, or document an explicit exception.

### OOS_9: [OUT_OF_SCOPE] voting-protocol dispatcher ownership repetition
- **Reviewer(s)**: dyn-dyn-dispatch-docs
- **Severity**: nit
- **Concern**: `skills/shared/voting-protocol.md:59-75` and `114-123` repeat dispatcher ownership three times (Overview, Voter Panel Composition, Launching Voters). Blunts context savings but does not break dispatch integration; live paths already bind to Python dispatchers.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_10: [OUT_OF_SCOPE] design/SKILL.md retains inline step-prefix encoding contract
- **Reviewer(s)**: dyn-dyn-prefix-docs
- **Severity**: important
- **Concern**: `skills/design/SKILL.md:37` still embeds the full `STEP_NUM_PREFIX` / `STEP_PATH_PREFIX` / `PARENT_SKILL_PATH` parsing contract inline. After extracting `step-prefix-encoding.md`, that makes a third authoritative surface. Plan scope kept `design/SKILL.md` untouched.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-prefix-docs: Replace inline encoding contract in `design/SKILL.md` with a pointer-only rule to `step-prefix-encoding.md`.

### OOS_11: [OUT_OF_SCOPE] review/SKILL.md missing step-prefix-encoding reference
- **Reviewer(s)**: dyn-dyn-prefix-docs
- **Severity**: important
- **Concern**: `/review` still accepts `--step-prefix` but has no progress-reporting section and no reference to `step-prefix-encoding.md`. Predates this branch. If nested `/implement` → `/review` breadcrumb dispatch is live, encoding discoverability remains fragile outside `design`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-prefix-docs: Add a progress-reporting pointer to `step-prefix-encoding.md` in `review/SKILL.md` when `--step-prefix` is used.

