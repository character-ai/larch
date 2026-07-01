## Decision 1: /research background fences stay out of bg-wait-coverage lint scope
- **Question**: Should /research's background fences (4 in research-phase.md + validation-phase.md) be brought into this lint's scope, or documented as an explicit, intentional exemption?
- **Resolution**: Document the exemption. Keep `skills/research/**` out of `SCOPE_PATTERNS`, but add an explicit code comment explaining why: /research always launches parallel background calls then waits via one foreground blocking collect call, never a bare "launch one thing, do nothing until `<task-notification>` fires" pattern like /design Step 3. /research also has no stall-recovery/pause-resume machinery that a `marker_step` registry entry would ever be read by.
- **Source**: user

## Decision 2: Do not redesign the lint's directive-to-fence matching algorithm
- **Question**: Should this fix also change `_nearest_launch_fence`'s proximity/ordering rules (12-line forward-only window, one fence per directive) to make brainstorm.md's two real launches detectable?
- **Resolution**: No. Add a properly-placed marker directive line directly before each of brainstorm.md's two external-launch fences (Framing, Scope), matching the established one-directive-per-fence convention already used in `skills/design/SKILL.md` and asserted by `test_accepts_current_design_and_implement_background_patterns`. This closes the coverage gap without touching the matching algorithm itself. A future author who places a marker directive too far from its fence (>12 lines, or after the fence) can still silently escape detection — this pre-existing algorithmic limitation is out of scope for this fix and will be called out as a residual risk, not fixed here.
- **Source**: codebase
