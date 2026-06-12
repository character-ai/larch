## Decision 1: Pre-bootstrap boundary
- **Question**: Which fences are pre-bootstrap and keep the old shape?
- **Resolution**: Explicitly: structured-invocation-pin (line 104), Preflight fences (lines 188-198), Step 0 initial bootstrap (line 241), dirty-tree recovery resume (line 283). Post-Step-0 starts at the degraded-tools gate (line 263) and continues through all later steps.
- **Source**: codebase (SKILL.md prose at line 122 names "Preflight, Step 0 initial invocation, legacy resume" plus "structured-invocation pin")

## Decision 2: larch-run.sh behavior
- **Question**: Exact behavior of larch-run.sh.
- **Resolution**: Sources plugin-root.env (guarded on CLAUDE_PLUGIN_ROOT being unset), falls back to awk extract from session-env.sh, exports CLAUDE_PLUGIN_ROOT and IMPLEMENT_TMPDIR, then execs "$CLAUDE_PLUGIN_ROOT/$1" with remaining args. Bash 3.2 portable (use `script=$1; shift; exec ... "$@"` pattern).
- **Source**: feature description

## Decision 3: Test shape acceptance
- **Question**: How does test-implement-fence-shape.sh handle two coexisting fence shapes?
- **Resolution**: Both shapes are valid. Old shape: canonical guard present + "$CLAUDE_PLUGIN_ROOT/..." call. New shape: `bash "$IMPLEMENT_TMPDIR/larch-run.sh" ...` call, no guard required. Test accepts either.
- **Source**: codebase (test logic + proposal)

## Decision 4: SKILL.md prose update
- **Question**: Does the "Bash block prelude" prose at lines 112-123 need updating?
- **Resolution**: Yes. The prose currently says every post-Step-0 fence must use the canonical guard. It must be updated to describe the new larch-run.sh shape as the standard post-Step-0 pattern.
- **Source**: codebase derivation

3 decisions resolved.
