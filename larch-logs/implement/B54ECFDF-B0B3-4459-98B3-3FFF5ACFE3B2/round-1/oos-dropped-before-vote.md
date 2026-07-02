### OOS_1: [OUT_OF_SCOPE] Brainstorm marker_step lacks runtime hook registration (documented scope trade-off)
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: `marker_step` `design-step1d5-brainstorm` is lint metadata only; it is not registered in `hook-bg-poll-guard.sh` / `hook-no-progress-guard.sh`, and `agent launch-review` does not write `.bg-wait-active`. Brainstorm external launches run without Monitor denial or no-progress circuit breaker during the launch-to-collect gap. Static lint acceptance does not add runtime notification-storm protection. The approved plan explicitly excludes runtime marker-writing for brainstorm; this is a documented scope trade-off, not a regression in this diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Add runtime marker plus hook STEP case in a follow-up, or document that brainstorm is intentionally unhooked.

### OOS_2: [OUT_OF_SCOPE] /research background launches remain outside bg-wait lint coverage
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-bg-wait-lint
- **Severity**: important
- **Concern**: Research background fences remain outside lint scope and unmarked at runtime. `SCOPE_PATTERNS` still excludes `skills/research/**`, so four `/research` background launch instructions bypass bg-wait coverage lint. This is intentional per the approved plan and encoded in tests, but the broader every-background-launch guarantee remains incomplete.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Accept documented exemption or widen SCOPE_PATTERNS in a follow-up if hooks should cover research.
  - From codex-specialist-correctness: Either widen SCOPE_PATTERNS to cover skills/research/** and add markers there, or codify the exemption as a separate documented contract/test.
  - From cursor-specialist-testing: Add a short note in `skills/research/SKILL.md` explaining the intentional exemption.

### OOS_3: [OUT_OF_SCOPE] Lint keys off prose run_in_background within 12 lines of fence
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-bg-wait-lint
- **Severity**: latent
- **Concern**: Lint still keys off any prose line containing `run_in_background: true` within 12 lines of a fence, not the canonical directive format alone. Prose at `skills/design/references/brainstorm.md:66` sits exactly 12 lines above the Framing fence, so `_nearest_launch_fence` can associate that prose line with the launch fence and green-light Framing even if the directive at line 77 were removed. Pre-existing `_nearest_launch_fence` behavior; plan forbade changing matching rules.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Move or shorten the prose block, or tighten `_nearest_launch_fence` to require the canonical directive format (out of scope for this plan).

### OOS_4: [OUT_OF_SCOPE] Brainstorm acceptance test does not guard directive persistence
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: `test_accepts_brainstorm_external_launches` would still return `rc == 0` if the `**⚠ Immediate-background required**` directive lines were removed, because no `run_in_background: true` line would fall within 12 lines of either fence. The test guards mapping shape, not directive persistence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add a negative fixture (fences only, no directives) asserting `rc == 1`, or assert violations for both slots.

### OOS_5: [OUT_OF_SCOPE] marker_step field is lint metadata only with no mechanical hook check
- **Reviewer(s)**: dyn-dyn-bg-wait-lint
- **Severity**: latent
- **Concern**: `CommandMapping.marker_step` is never read during linting; coverage is command-substring only. That predates this branch, but the new brainstorm entry continues the pattern of registering a `marker_step` label with no mechanical check that hooks or runtime writers implement it.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_6: [OUT_OF_SCOPE] Brainstorm mapping may block unrelated launch-review fences that share only timing tokens
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: The brainstorm mapping is narrower than an ideal design-review shape: requiring `brainstorm-output.txt` in `--output` blocks unrelated `launch-review` fences that only share `-brainstorm` timing.
- **Suggested revisions (informational for voters; coder decides)**:

