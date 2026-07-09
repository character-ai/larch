### FINDING_1: [OUT_OF_SCOPE] function-local imports are invisible to resolution
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: The import map is module-level only; function-local imports are invisible to resolution, so a monkeypatch against a locally imported facade can slip through.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Extend per-scope import tracking in `_collect_scope`, or document as a V1 skip with suppression guidance.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_2: [OUT_OF_SCOPE] imported alias rebinding is not tracked per scope
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Name resolution ignores same-scope rebinding of imported aliases, so a local assignment can masquerade as an imported module and still be treated as a facade patch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Track assignments that rebind imported names within each scope before calling `_resolve_expr_module`.
  - From cursor-specialist-edge-cases: Track per-scope bindings or skip when a same-name local assignment precedes the setattr (future V2).


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_3: dotted imports collapse to the root package
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases
- **Severity**: major
- **Concern**: Plain unaliased dotted imports are collapsed to the root package, so resolving `larch.report.run_logs` depends on parent packages re-exporting children and can miss imported repo modules.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Preserve full unaliased dotted imports, or resolve the longest imported dotted prefix before walking re-exported attributes.
  - From codex-specialist-edge-cases: Preserve the full imported module for non-aliased dotted imports and resolve the longest matching attribute prefix before walking facade re-exports. Add a regression test for `import larch.report.run_logs` plus `monkeypatch.setattr(larch.report.run_logs, "...", ...)`.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_5: [OUT_OF_SCOPE] lint catalog omits the new ratchet
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: The linting catalog does not mention the new monkeypatch-facade-binding ratchet, so operators may miss suppression syntax, regen target, and pytest path when triaging failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Add a catalog row matching sibling ratchet lints.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_6: [OUT_OF_SCOPE] check mode warning noise can hide new findings
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Check mode emits one warning per baselined finding, so new unbaselined violations are easy to miss in noisy CI stderr.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Emit only new findings by default, or add a summary line with the new-count.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_8: [OUT_OF_SCOPE] grandfathered facade patches remain unretargeted
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Grandfathered facade patches for `_commit_run` remain instead of being retargeted, so the silent-no-op risk persists in baselined tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Follow-up outside this feature: retarget patches to defining or consuming modules and shrink baseline.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_9: [OUT_OF_SCOPE] new lint tests lack explicit shard assignments
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The new lint tests do not have explicit shard assignments, so they still run via round-robin and shard balance may drift until the next rebalance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Refresh shard assignments when rebalancing CI shards.
Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

