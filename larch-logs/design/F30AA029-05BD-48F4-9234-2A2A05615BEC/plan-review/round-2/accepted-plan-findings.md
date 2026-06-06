### FINDING_1: Step 5 banner values are computed in an isolated Bash subprocess
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Codex-Requirements, Cursor-dyn-shell-contract-drift
- **Severity**: important
- **Concern**: Step 5 banner-prep computes `prior_degraded_rounds` / `effective_round_cap` inside a Bash tool subprocess, but the subsequent banner remains prompt-side prose. Because Bash state is not preserved across calls and the prep emits no parseable values, the orchestrator may not have reliable banner values and may print empty/literal/stale variables or reimplement the calculation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Make the Bash block emit parseable KVs or print the complete banner itself, including dynamic_archetypes_cap, before run-step5-review starts
  - From Codex-Innovation: Have the existing Step 5 prelude fence either print the final banner itself or emit parsed KVs for the orchestrator before printing; avoid adding a new rehydration fence, or update the timing-rehydration harness and sibling docs counts if a new fence is truly needed
  - From Codex-Requirements: Fold the CLI call and banner printf into the same Bash block, or emit parseable KV lines for effective_round_cap/dynamic_archetypes_cap and instruct the orchestrator to parse them before printing the banner
  - From Cursor-dyn-shell-contract-drift: Either echo machine-readable stdout from the fence (`effective_round_cap=<n>` / `prior_degraded_rounds=<n>`) and instruct the orchestrator to parse it before printing, or move the banner `printf` into the same fenced block (keep `dynamic_archetypes_cap` prose-derived as today)


### FINDING_2: Added Step 5 fence would break pinned rehydration/count harnesses
- **Reviewer(s)**: Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-dyn-shell-contract-drift
- **Severity**: important
- **Concern**: The proposed Step 5 banner-prep adds another fenced Bash prelude with `IMPLEMENT_TMPDIR` assignment/export and `plugin-root.env` guard, but the plan does not update byte/cardinality-pinned timing-rehydration expectations. Relevant checks may fail because guard and assignment/export counts drift from the harness’s expected totals.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Update the rehydration harness and docs counts, or avoid a new fence by reusing the existing Step 5 invocation fence while keeping the run-step5-review argv unchanged
  - From Cursor-Innovation: [SCOPE-REDUCTION] Fold banner-prep into the existing run-step5-review.sh fence (skills/implement/SKILL.md:789-795) without new IMPLEMENT_TMPDIR assign/export lines, or add scripts/test-implement-timing-rehydration.sh to Files to modify with updated expected counts
  - From Codex-Innovation: Have the existing Step 5 prelude fence either print the final banner itself or emit parsed KVs for the orchestrator before printing; avoid adding a new rehydration fence, or update the timing-rehydration harness and sibling docs counts if a new fence is truly needed
  - From Cursor-Pragmatic: Fold banner-prep into the existing Step 5 telemetry fence (already has IMPLEMENT_TMPDIR + plugin-root rehydration) instead of a third Step 5 fence; or keep the new fence and update `test-implement-timing-rehydration.sh` expected counts plus the SKILL.md "42 executable rehydration sites" prose at skills/implement/SKILL.md:115
  - From Codex-dyn-shell-contract-drift: Revise the plan to extend the existing Step 5 setup fence at skills/implement/SKILL.md:770-775 and reuse its IMPLEMENT_TMPDIR export/root source, or explicitly include the required test-implement-timing-rehydration expectation update if a separate block is intentional.


### FINDING_3: Missing script-md sibling stub for touched round-cap harness
- **Reviewer(s)**: Codex-Edge
- **Severity**: latent
- **Concern**: The plan updates `scripts/test-lib-implement-round-cap.sh` but does not add the required neighboring `.md` stub, leaving the edited harness outside the repository’s script-md-siblings contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Add scripts/test-lib-implement-round-cap.md as a short stub naming scripts/lib-implement-round-cap.sh as the primary contract and make test-lib-implement-round-cap as the target, matching the new append-execution harness pattern


### FINDING_4: Bash block prelude docs omit the initial Step 0 wrapper self-derive contract
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The plan omits updating the Bash block prelude documentation for the initial Step 0 case where `CLAUDE_PLUGIN_ROOT` is not yet available from tmpdir rehydration. Without this, the docs may continue to imply plugin-rooted helpers are infeasible until post-Step-0 rehydration, recreating the documented contract gap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add a short Bash block prelude bullet: initial Step 0 may call implement-bootstrap-invoke.sh before tmpdir exists; the wrapper self-derives and exports CLAUDE_PLUGIN_ROOT from $0 when unset; post-Step-0 rehydration via plugin-root.env unchanged


### FINDING_5: Step 0 fallback placeholder may not be loader-expanded
- **Reviewer(s)**: Cursor-dyn-shell-contract-drift
- **Severity**: important
- **Concern**: The Step 0 fallback uses a non-repo `<installed-plugin-root>` placeholder instead of the skill-loader `${CLAUDE_PLUGIN_ROOT}` expansion pattern. A literal paste could leave `CLAUDE_PLUGIN_ROOT` wrong or empty before the wrapper self-derive runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-shell-contract-drift: Use the same pattern as `skills/design/SKILL.md` and `SECURITY.md`: `[ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && CLAUDE_PLUGIN_ROOT='${CLAUDE_PLUGIN_ROOT}'` (loader-expanded) before `export CLAUDE_PLUGIN_ROOT`, and pin that literal in `scripts/test-implement-structure.sh` if needed


### FINDING_6:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:783-791; scripts/test-implement-timing-rehydration.sh:144-162
- **Concern**: [SCOPE-REDUCTION] Planned Step 5 banner prep is a separate side-effect-only Bash block with extra rehydration/export lines. Scenario: The Bash tool does not preserve shell variables, so assigned effective_round_cap is unavailable to the markdown banner unless the block emits it or prints the banner in the same shell; adding another plugin-root guard and IMPLEMENT_TMPDIR export also trips the exact-count rehydration harness
- **Proposed resolution**: Keep the computation in the existing Step 5 invocation fence and print the banner there before run-step5-review.sh, or emit parseable EFFECTIVE_ROUND_CAP from the prep block; drop the unnecessary IMPLEMENT_TMPDIR self-assignment/export and avoid adding a second plugin-root guard unless the timing test is updated intentionally


### FINDING_7:
- **Reviewer(s)**: Cursor-dyn-scope-control
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:298-308 (proposed Step 0 edit)
- **Concern**: [SCOPE-REDUCTION] Item 1 adds a Step 0 SKILL.md CLAUDE_PLUGIN_ROOT literal fallback plus caller-level harness coverage beyond the approved outline which scoped SKILL edits to the Step 5 banner only. Scenario: The #3448 failure was implement-bootstrap-invoke.sh:32 with the wrapper already reached via template-expanded paths; wrapper self-derive+export fixes that without a SKILL prelude. Dual layers duplicate the issue's either/or remediations and widen review/structure-test surface
- **Proposed resolution**: Limit Item 1 to scripts/implement-bootstrap-invoke.sh self-derive+export (and its .md/test). Drop the proposed Step 0 caller fallback block and the mirror caller-level harness case; keep only the unset-CLAUDE_PLUGIN_ROOT direct-wrapper invoke test


### FINDING_8:
- **Reviewer(s)**: Codex-dyn-scope-control
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:298-308; .claude/rules/skill-runtime-root-paths.md:1-7
- **Concern**: [SCOPE-REDUCTION] Step 0 SKILL fallback exceeds the approved surface and invites a public-SKILL hardcoded root. Scenario: The approved direction limits skills/implement/SKILL.md work to the Scripted review loop banner, while current public skill paths use ${CLAUDE_PLUGIN_ROOT}/...; the plan adds a Step 0 pre-wrapper fallback using an <installed-plugin-root> literal/path source, broadening the startup contract and risking machine/cache path drift in shipped prompt text
- **Proposed resolution**: Drop the Step 0 SKILL.md fallback, its implement-bootstrap-invoke.md note, and the caller-level no-tmpdir test; keep the wrapper self-derive/export change plus a direct-wrapper unset-env test. If caller fallback is truly required, send it back for explicit scope approval and express it without literal installed paths

