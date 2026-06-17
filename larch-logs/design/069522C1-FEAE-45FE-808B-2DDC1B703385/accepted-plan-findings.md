### FINDING_2: Child CLI subprocesses must resolve from CLAUDE_PLUGIN_ROOT
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Production bash resolves `CLI` from `PLUGIN_ROOT/python/cli.py` where `PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-…}"` (`scripts/dispatch-code-voters.sh:11–12`). Harness fixtures stub only `$voter1_plugin/python/cli.py` and delegate some verbs to `REAL_CLI`. If `agent_voters.py` hardcodes `Path(__file__)` for child invocations (`render voter`, `launch-claude-review`, `dispatch-waterfall`, `wait-reviewers`, `parse-rate-retry`), stub interception breaks: late-sentinel and parallel-dispatch regressions either fail or exercise the wrong code.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Resolve plugin_root via os.environ.get("CLAUDE_PLUGIN_ROOT") with the same repo-root fallback as agents._plugin_root and build every child argv from plugin_root / "python" / "cli.py"


