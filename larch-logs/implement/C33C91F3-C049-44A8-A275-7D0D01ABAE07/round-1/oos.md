### FINDING_1: [OUT_OF_SCOPE] Known-correct facade patches are still ratcheted as warnings
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-static-resolver
- **Severity**: major
- **Concern**: The baseline/ratchet path still grandfathers existing facade patches and can continue flagging correct consumer-module or late-lookup facade patches, so the warnings do not cleanly separate intentional baselines from broken bindings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: `Narrow to facade/re-export modules, or exempt patches where M is the direct consumer/importer; stop baselining the correct run_log_flush pattern.`


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_2: [OUT_OF_SCOPE] `from`-import bindings lose their submodule path
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-static-resolver
- **Severity**: major
- **Concern**: `_import_binding_source` reports only the base package for `from … import …` bindings, so defining-module text and baseline identity can point at the package instead of the imported submodule.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: `If that import form matters later, treat alias.name as a submodule segment when statement.module is empty and level > 0.`
  - From dyn-dyn-static-resolver: `Pass ModuleResolver into _import_binding_source (or mirror its candidate logic) so defining-module text is f"{base_module}.{alias.name}" when source_for_module(...) succeeds, otherwise base_module; add fixtures for from larch.core import proc, from larch import io as larch_io, and from . import sub, then regen the baseline.`


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_3: [OUT_OF_SCOPE] Test-file resolution ignores lexical-scope imports
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, dyn-dyn-static-resolver
- **Severity**: major
- **Concern**: The import map is built only from module-level imports, so function- or class-local imports can be silently skipped when resolving monkeypatch targets.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: `Only extend this if function-scoped imports become a common test pattern; scope-local import maps would be needed.`
  - From codex-specialist-correctness: `Build the import map per lexical scope, or collect imports from the enclosing function or class before resolving the monkeypatch target.`
  - From dyn-dyn-static-resolver: `Bounded fix: accumulate imports per lexical scope while walking _collect_scope, or document the limitation explicitly in the lint module docstring.`


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_10: [OUT_OF_SCOPE] linting catalog omits the new ratchet row
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The linting catalog does not list the new ratchet row, so operators can miss the suppression syntax, regen target, and pytest path when triaging failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: `Add a catalog row mirroring tempfile-dir when docs updates are in scope.`


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_11: [OUT_OF_SCOPE] check mode floods baselined warnings
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Check mode emits one warning per baselined row, so new unbaselined violations can be hard to spot in CI stderr among grandfathered warnings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: `Consider a summary-only quiet mode for check, or document log filtering; optional follow-up outside this feature scope.`


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_12: [OUT_OF_SCOPE] new lint tests lack shard assignment
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The new lint tests are not shard-assigned, so they fall back to round-robin balancing until the shard map is refreshed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: `Refresh shard assignments via /rebalance-tests when convenient.`


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_15: [OUT_OF_SCOPE] same-scope rebinding is not checked
- **Reviewer(s)**: dyn-dyn-static-resolver
- **Severity**: minor
- **Concern**: Resolution maps a `Name` to the module-level import table with no check for same-scope rebinding, so a local assignment like `facade = Mock()` can be mistaken for the imported module.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-static-resolver: `A narrow fix is to track simple ast.Assign/ast.AnnAssign to imported names within each function body before resolving.`
Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

