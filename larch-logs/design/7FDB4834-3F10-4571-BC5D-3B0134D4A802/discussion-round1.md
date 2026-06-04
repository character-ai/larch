## Decision 1: Placement of the restored Step 9a.1 procedure
- **Question**: Inline `## Step 9a.1` section in SKILL.md vs separate reference file?
- **Resolution**: New `skills/implement/references/oos-pipeline.md` + a MANDATORY load directive in SKILL.md; repoint the broken `step 3.4 / 3.4b` citations to it. Matches the references/*.md convention; durability comes from the new CI guard.
- **Source**: user (Step 1c)

## Decision 2: Fidelity to PR #1896
- **Question**: Verbatim restore of #1896 text vs reconstruct against current code?
- **Resolution**: Reconstruct to current code — use #1896 as the structural skeleton but write against today's helpers (oos-issue-cap.sh, oos-file-conflict-deps.sh, oos-disposition-checkpoint.sh) and current carve-outs (design-phase exclude-already-filed, fork-mode, repo_unavailable, NEVER #5 ndjson append, current larch-logs batches). Avoid stale paths removed by the larch-logs refactor (#1438).
- **Source**: user (Step 1c)

## Decision 3: No OOS-pipeline behavior change
- **Question**: Does this change OOS pipeline behavior/capability?
- **Resolution**: No. Issue states this is a "documentation/structure regression + missing guard, not a missing capability." Restore the documented procedure, pin the sentinel format, add a CI guard. Do NOT alter helper invocation order, triage rules, voting, or filing behavior.
- **Source**: codebase/issue

## Decision 4: Format-pin scope
- **Question**: Pin oos-issues-created.md format for /implement only, or unify with /design's writer too?
- **Resolution**: /implement Step 9a.1 scope only (the issue is implement-scoped). The pinned format must satisfy BOTH the disposition gate's loose URL-token grep (`--filed-urls-file`) AND Invariant #1 idempotent URL+tally recovery. Cross-reference oos-disposition-gate.md counting rules. Do not refactor /design's file-design-oos.sh; keep it compatible.
- **Source**: codebase/issue

## Decision 5: Regression guard scope
- **Question**: What must the new test-implement-structure.sh assertion cover?
- **Resolution**: Assert (a) the Step 9a.1 procedure surface exists (oos-pipeline.md present + the MANDATORY load directive in SKILL.md), (b) the `step 3.4 / 3.4b` citations resolve to it, and (c) the oos-issues-created.md format-pin anchor is present. Must be robust against the awk-boundary fragility noted in #1477.
- **Source**: codebase/issue

## Hard constraints (must not break)
- Security findings are NEVER filed via the OOS path (route through SECURITY.md private disclosure).
- Fork-mode (`forked_target=true`) and `repo_unavailable=true` carve-outs must be preserved (skip filing).
- NEVER #5: idempotent-rerun branch must still write oos-issues / run-statistics larch-log batches.
- Step 9a.1 combine pass MUST exclude `### OOS_` blocks already carrying `- **Filed URL**:` (design-phase carve-out).
- oos-disposition-checkpoint must still gate OOS_PENDING clearing.
