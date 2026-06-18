## Decision 1: Module placement for design_clarify_main
- **Question**: Should design_clarify_main go in python/clarify.py or python/design_lifecycle.py?
- **Resolution**: python/clarify.py — the issue scope explicitly lists it; all clarify primitives already live there; the phase driver directly orchestrates those primitives.
- **Source**: user

## Decision 2: Bash script fate
- **Question**: Should design-clarify.sh be deleted or kept as thin delegation wrapper?
- **Resolution**: Thin delegation wrapper — the design-run-$PPID.sh launcher resolves scripts by .sh filename; deleting the file would break the launcher without additional changes. Wrapper sources session env, checks pause, execs python3 cli.py design clarify.
- **Source**: user

## Decision 3: Cross-module subprocess vs direct Python calls in publish phase
- **Question**: Should publish-phase calls to named-block write, design log-publish, tracking-issue rename use subprocess or direct Python module imports?
- **Resolution**: Subprocess via _cli_cmd pattern (same as design_lifecycle.py) for cross-module calls; direct function calls for clarify_state, clarify_comment_fetch, clarify_comment_post, clarify_label (same module). redact.redact() called directly since clarify.py already imports redact.
- **Source**: codebase

## Decision 4: Plugin root resolution in clarify.py
- **Question**: How does design_clarify_main find the plugin root for subprocess calls?
- **Resolution**: Read os.environ.get("CLAUDE_PLUGIN_ROOT"); fall back to Path(__file__).resolve().parents[1] (python/ parent = larch root). Thin wrapper sets CLAUDE_PLUGIN_ROOT before calling Python.
- **Source**: codebase

## Decision 5: stage_failed_clarify equivalent
- **Question**: Should design_clarify_main replicate the bash stage_failed_clarify (calls design-stage-terminal-state.sh)?
- **Resolution**: Yes, call design-stage-terminal-state.sh via subprocess on fetch-phase failures. design-stage-terminal-state.sh is not being ported in G6.1. Pattern mirrors step0_clarify_hard_halt_main in design_lifecycle.py.
- **Source**: codebase

## Decision 6: test-design-clarify.sh fate
- **Question**: Should the existing bash harness be kept, updated, or deleted?
- **Resolution**: Update test-design-clarify.sh to test the thin wrapper behavior (that it delegates to Python, that pause-save fires when .pause-requested exists). Python unit tests for design_clarify_main go in test_clarify.py.
- **Source**: codebase
