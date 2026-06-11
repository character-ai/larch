## Decision 1: is_scope_reduction_block portability
- **Question**: Should `is_scope_reduction_block` be ported to Python or left in bash?
- **Resolution**: Not ported. The plan explicitly delegates to `scripts/check-scope-reduction-marker.sh`; its one non-test caller (`test-plan-review-scope-anchor.sh`) is retargeted per the UPDATED file list.
- **Source**: codebase

## Decision 2: F1 dependency (proc.py / logging_util.py)
- **Question**: Is F1 (the Python foundation) already available to build on?
- **Resolution**: Yes. `python/proc.py` (144 lines) and `python/logging_util.py` (182 lines) with `quiet_init`, `emit_kv`, and `contract_stream` exist and match what `voting.py` will call.
- **Source**: codebase

## Decision 3: Stdlib-only constraint
- **Question**: Any third-party imports allowed in voting.py?
- **Resolution**: Stdlib-only per issue definition-of-done and `python/README.md` conventions. No new dependencies.
- **Source**: codebase

## Decision 4: Bash 3.2 compatibility of consumers
- **Question**: Must consumer edits (dispatch-code-voters.sh, dispatch-plan-voters.sh) stay Bash 3.2-safe?
- **Resolution**: Yes. The plan specifies "Bash 3.2-safe indexed array" for `VPR_ARGS` construction.
- **Source**: codebase

0 user-answered decisions; 4 codebase-resolved decisions.
