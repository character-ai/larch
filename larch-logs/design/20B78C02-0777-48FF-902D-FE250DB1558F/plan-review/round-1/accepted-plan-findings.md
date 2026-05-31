### FINDING_1: Invariant C still enforces awk rehydration after plugin-root.env migration
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan retires grep parity at `scripts/test-implement-timing-rehydration.sh:128-132` but leaves Invariant C (`:78-103`) requiring same-fence `LARCH_CLAUDE_PLUGIN_ROOT=` plus `awk` rehydration for every fence using `${CLAUDE_PLUGIN_ROOT}`. After `skills/implement/SKILL.md` switches to sourcing `plugin-root.env`, fences that only source that file would fail Invariant C; `make test-implement-timing-rehydration` / `make lint` would break even if the new grep checks pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend the `### UPDATED: scripts/test-implement-timing-rehydration.sh` step: rewrite Invariant C (lines 78-103) to treat `plugin-root.env` sourcing as the guard (e.g. `plugin-root.env` plus `. "$IMPLEMENT_TMPDIR/plugin-root.env"`); update the file header comment (lines 17-20) and `scripts/test-implement-timing-rehydration.md` invariant 4 to match
  - From Cursor-Pragmatic: Extend the plan to rewrite Invariant C (and scripts/test-implement-timing-rehydration.md invariant 4) to treat plugin-root.env sourcing as the same-fence guard; drop the awk-only detector


### FINDING_2: Resume/dirty-tree paths lack plugin-root.env for legacy tmpdirs
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Resume and dirty-tree recovery rehydrate `CLAUDE_PLUGIN_ROOT` from `session-env.sh` (e.g. `skills/implement/SKILL.md:307-311`, `:466-469`), but a plan that switches SKILL fences to `plugin-root.env` only does not cover legacy tmpdirs where `implement-bootstrap.sh` resume-plan-tail (`557-586`) skips `write-session-env.sh`: `session-env.sh` exists without `plugin-root.env`. Pre-bootstrap Step 0 rehydration and dirty-tree recovery can no-op; `${CLAUDE_PLUGIN_ROOT}/scripts/...` calls then fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Either (a) keep session-env.sh awk fallback only when plugin-root.env is absent at those pre-bootstrap sites, or (b) add a minimal resume sync in implement-bootstrap.sh that emits plugin-root.env from LARCH_CLAUDE_PLUGIN_ROOT when session-env.sh exists and sibling is missing

