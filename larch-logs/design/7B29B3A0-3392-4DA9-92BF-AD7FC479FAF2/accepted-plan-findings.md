### FINDING_1: Add agent-lint exclude for Makefile-only bash32 harness
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Edge, Codex-Edge, Codex-Innovation, Codex-Pragmatic, Cursor-Innovation, Cursor-Requirements, Cursor-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: The new `scripts/test-render-final-summary-bash32.sh` harness is Makefile-only, and existing precedent requires explicit `agent-lint.toml` exclusion because agent-lint does not follow Makefile reachability. Without the exclude, `make lint` / CI can fail with a dead-script or unreachable-script finding.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Codex-Arch, Cursor-Edge, Codex-Edge, Codex-Innovation, Codex-Pragmatic: Add scripts/test-render-final-summary-bash32.sh to the [lint].exclude array with the nearby Makefile-only harnesses; add the .md too only if agent-lint flags sibling markdown in this repo's current rule set
  - From Cursor-Innovation, Cursor-Requirements: Add scripts/test-render-final-summary-bash32.sh (and sibling .md) to agent-lint.toml exclude with the same Makefile-only comment shape as test-collect-agent-bash32.sh; mention it in scripts/test-render-final-summary-bash32.md
  - From Cursor-Pragmatic: Add an `agent-lint.toml` exclude block for `scripts/test-render-final-summary-bash32.sh` (comment: issue #3039, Makefile-only via `test-render-final-summary-bash32`), mirroring the `test-collect-agent-bash32.sh` entry
  - From Codex-Requirements: Add `scripts/test-render-final-summary-bash32.sh` to `agent-lint.toml` near the existing bash32 harness exclusion, with the same Makefile-only rationale; include the `.md` stub too if agent-lint flags sibling docs in this repo pattern.


### FINDING_2: Case 2 checks the wrong stderr surface
- **Reviewer(s)**: Cursor-Innovation, Codex-Pragmatic
- **Severity**: important
- **Concern**: The proposed bash 3.2 regression test can pass while the target bug still occurs because `invoke_render` stderr is redirected into `$DESIGN_TMPDIR/render-final-summary.stderr.log`, fallback can still produce `final-summary.md`, and the outer harness stderr plus `rc=0` assertions do not prove the array/nounset failure was avoided.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Gate Case 2 on ! grep -q 'unbound variable' "$DESIGN_TMPDIR/render-final-summary.stderr.log" (and/or drop the rc=0 requirement); mirror scripts/test-create-pr.sh by invoking a path whose failure surfaces on the harness stderr only if you add a minimal wrapper
  - From Codex-Pragmatic: Have Case 2 also assert DESIGN_TMPDIR/render-final-summary.stderr.log and execution-issues.md do not contain unbound variable or a render-run-summary fallback warning


### FINDING_3: Harness must clear issue-bound publishing state
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: The proposed harness invocation does not clear `ISSUE_NUMBER`, so running it from an issue-bound developer environment could trigger `tracking-issue-summary.sh upsert-summary` during `--post-publish-only` and mutate GitHub comments from a regression test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Invoke the subject with ISSUE_NUMBER="" and a test SESSION_ID, plus explicit DESIGN_TMPDIR and CLAUDE_PLUGIN_ROOT, so the harness is hermetic


### FINDING_4: Place new harness in the balanced Makefile shard
- **Reviewer(s)**: Cursor-dyn-shard-registry, Codex-dyn-shard-registry
- **Severity**: latent
- **Concern**: The plan puts the new harness in `test-harnesses-12`, but the current Makefile shard-balance narrative says shards 5-20 are packed by equal harness count, and shard 12 is already larger than shard 14. Adding another test there worsens the documented imbalance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-shard-registry, Codex-dyn-shard-registry: Revise the Makefile step to place test-render-final-summary-bash32 in test-harnesses-14 unless the plan explicitly waives the documented equal-count balance. The .PHONY instruction to add the target on Makefile:4 and the target-rule insertion after test-render-final-summary at Makefile:468-469 both match the actual Makefile and can stay.


### FINDING_5: Case 1 static grep contract is too loose
- **Reviewer(s)**: Cursor-dyn-precedent-fidelity, Codex-dyn-precedent-fidelity
- **Severity**: important
- **Concern**: The proposed static grep test is inconsistent about the number of greps and does not provide literal regexes. Because there are two important code sites to pin, an implementer could write a loose check that passes a partial fix or adds unnecessary grep complexity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-precedent-fidelity, Codex-dyn-precedent-fidelity: Revise Case 1 to give the literal grep patterns and pick one count. Minimum-change version: two greps wired with &&, one matching the guarded COST_ARGS copy into render_cost_args and one matching the render-run-summary invocation line with both render_cost_args[@]+ and note_args[@]+ guards.

