### [Plan Review] FINDING_11

### FINDING_11: hooks/hooks.json line numbers off by one in plan

- **Reviewers**: Cursor-Requirements, Codex-Requirements (2/10 — counted as one across reviewers)
- **Concern**: The plan cites `hooks/hooks.json` lines 23-32 for the Skill matcher block; the current block is at lines 24-33.
- **Proposed resolution**: Refresh the line numbers, or anchor by JSON-path / structural description (`PreToolUse → Skill matcher block`).


### [Plan Review] FINDING_14

### FINDING_14: Final grep include set too narrow — extensionless files / Dockerfile may hide references

- **Reviewers**: Cursor-Edge (1/10)
- **Concern**: The plan's final `grep --include='*.md' --include='*.sh' …` set may miss configuration files without recognized extensions (Dockerfile, CI YAML variants, extensionless scripts).
- **Proposed resolution**: Either extend the include globs to cover these formats, or document a second audit pass / accepted leftover surface.


### [Plan Review] FINDING_17

### FINDING_17: Operator/CI guidance for fail-open shift in skip semantics

- **Reviewers**: Cursor-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Requirements (4/10)
- **Concern**: The current helper fails closed when the check script is absent (exit 127 + STATUS=fail). The plan changes that to a success-equivalent skip. CI or wrappers that key only on exit status would see the skip as success. Consumers should have guidance for asserting checks ran (e.g., grepping for `RELEVANT_CHECKS_OK=true` rather than relying on rc=0).
- **Proposed resolution**: Pair the CHANGELOG entry with explicit consumer guidance: treat `RELEVANT_CHECKS_SKIPPED=true` as a first-class signal; where checks are mandatory, CI must fail when that token appears. Optionally add a `LARCH_RELEVANT_CHECKS_REQUIRED=1` env switch that makes the wrapper fail-closed on the skip path (low-cost feature flag for operators who want strict enforcement).


### [Plan Review] FINDING_18

### FINDING_18: Hook deletion premature — keep through migration window

- **Reviewers**: Codex-Innovation, Codex-Pragmatic (2/10)
- **Concern**: Deleting `scripts/hook-block-skill-relevant-checks.sh` removes the active-session backstop while stale consumer repos may still ship a project-local `/relevant-checks` skill. During the migration window, an orchestrator could accidentally invoke that skill via the Skill tool, bypassing the wrapper / redaction contract.
- **Proposed resolution**: Keep the hook for at least one release, update its deny reason to point at `scripts/relevant-checks.sh`, and delete only after the residual legacy-Skill risk is intentionally dropped.
- **NOTE FOR VOTERS**: This finding directly contradicts the user's explicit Step 1c decision: "Delete hook + registration (recommended) — Remove `scripts/hook-block-skill-relevant-checks.sh`, its `.md` sibling, its test, and the registration in `hooks/hooks.json`. Consistent with the 'clean up all references' directive." Voters should consider whether to override the explicit user decision based on the merits.


### [Plan Review] FINDING_19

### FINDING_19: Innovation — ship a thin default scripts/relevant-checks.sh as plugin template

- **Reviewers**: Cursor-Innovation (1/10)
- **Concern**: Rather than relying on documentation alone to communicate the new contract, ship a default `scripts/relevant-checks.sh` (or `scripts/relevant-checks.default.sh` that consumers symlink/copy) in the plugin template so fresh installs rarely hit the skip path.
- **Proposed resolution**: Out-of-scope alternative; would add a separate template-distribution mechanism. Mentioned as an option, not a required change for this PR.


