### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-implement-timing-rehydration.sh:78-103
- **Concern**: Invariant C still requires same-fence awk rehydration (`LARCH_CLAUDE_PLUGIN_ROOT=` + `awk`) but the plan only retires the grep parity at 128-132. Scenario: After SKILL.md switches to sourcing `plugin-root.env`, every fence using `${CLAUDE_PLUGIN_ROOT}` fails Invariant C and `make test-implement-timing-rehydration` / `make lint` breaks even if the new grep checks pass
- **Proposed resolution**: Extend the `### UPDATED: scripts/test-implement-timing-rehydration.sh` step: rewrite Invariant C (lines 78-103) to treat `plugin-root.env` sourcing as the guard (e.g. `plugin-root.env` plus `. "$IMPLEMENT_TMPDIR/plugin-root.env"`); update the file header comment (lines 17-20) and `scripts/test-implement-timing-rehydration.md` invariant 4 to match

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:307-311,466-469
- **Concern**: Resume/dirty-tree paths rely on session-env.sh but plan switches to plugin-root.env only. Scenario: implement-bootstrap.sh resume-plan-tail (557-586) skips write-session-env.sh; legacy tmpdirs have session-env.sh but no plugin-root.env. Pre-bootstrap rehydration at Step 0 and dirty-tree recovery no-op; ${CLAUDE_PLUGIN_ROOT}/scripts/... calls fail.
- **Proposed resolution**: Either (a) keep session-env.sh awk fallback only when plugin-root.env is absent at those pre-bootstrap sites, or (b) add a minimal resume sync in implement-bootstrap.sh that emits plugin-root.env from LARCH_CLAUDE_PLUGIN_ROOT when session-env.sh exists and sibling is missing.

### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-implement-timing-rehydration.sh:78-103
- **Concern**: Plan updates grep assertions at 128-132 but not Invariant C awk fence scanner. Scenario: After SKILL.md switches to sourcing plugin-root.env, Invariant C still requires LARCH_CLAUDE_PLUGIN_ROOT= plus awk in the same fence; make test-implement-timing-rehydration / make lint fails even if the new source-line grep passes
- **Proposed resolution**: Extend the plan to rewrite Invariant C (and scripts/test-implement-timing-rehydration.md invariant 4) to treat plugin-root.env sourcing as the same-fence guard; drop the awk-only detector
