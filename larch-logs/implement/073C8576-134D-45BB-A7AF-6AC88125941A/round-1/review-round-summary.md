# Review Round 1

- Mode: `diff`
- 2 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_2: `_emit_final_summary_marked_from_disk` breaks `FINAL_SUMMARY_PATH` contract
- **Reviewer(s)**: codex-generalist
- **Severity**: important
- **Concern**: `python/larch/design/design_terminal.py:741-753` — `_emit_final_summary_marked_from_disk` no longer emits `FINAL_SUMMARY_PATH` and now writes the full summary body between `LARCH_FINAL_SUMMARY_BEGIN/END`. The existing `/design` contract expects `FINAL_SUMMARY_PATH=<path>` plus empty readiness markers, as reflected by `skills/shared/final-summary-emit.md` and existing tests in `python/test_design_lifecycle.py:663-671`. A Step 5c or final-summary notification will now lack the path the orchestrator is instructed to parse.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generalist: Restore the old contract: emit `logging_util.emit_kv(key=config.ENV_FINAL_SUMMARY_PATH, value=str(summary_path))`, emit empty markers only, and leave summary body reading to the orchestrator.


### FINDING_3: Split-function complexity baseline rows moved instead of removed
- **Reviewer(s)**: codex-generalist
- **Severity**: important
- **Concern**: `python/complexity-baseline.json:1035-1362` — The split-function complexity baseline rows were moved to the new modules instead of removed, and `python/ruff.toml:291-374` keeps broad complexity ignores for the shim and every split module. This misses the plan acceptance item that required removing the split functions from the complexity baseline and unnecessary per-file ignores.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generalist: Decompose or reduce the remaining over-threshold functions enough to remove these baseline rows, then narrow or remove the corresponding `ruff.toml` ignores, especially the obsolete `design_lifecycle.py` block.


