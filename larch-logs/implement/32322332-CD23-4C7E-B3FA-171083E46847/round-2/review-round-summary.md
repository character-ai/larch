# Review Round 2

- Mode: `diff`
- 6 accepted, 4 rejected (1 neutral)

## Accepted Findings

### FINDING_1: close-original lacks idempotency guard
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `close_original_issue` / `decompose close-original` is not idempotent after success. Operator retries post duplicate `gh` issue comments and may error on an already-closed issue because `.decompose-original-closed` is not checked at entry and `comment_sent` handling allows re-commenting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Check .decompose-original-closed sentinel at entry and return ok without re-commenting
  - From cursor-specialist-edge-cases-output.txt: Short-circuit when .decompose-original-closed exists; avoid deleting comment_sent until idempotent close is verified


### FINDING_10: missing pytest for prompt-override fail-closed and context-path containment
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Missing pytest for prompt-override fail-closed and context-path containment required by the plan. Regressions in `_validate_prompt_override` or `_validate_context_file` could allow reading staging files outside allowed roots or accepting unsafe overrides without a failing test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add pytest for invalid override paths, symlink/size rejection, outside-root context files, and retry-without-override behavior


### FINDING_11: dynamic scout warning emission crashes on CR/LF in invalid names
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: Dynamic scout warning emission can crash on untrusted invalid names containing CR/LF. `validate_dynamic_manifest()` can place the raw rejected `name` in a warning, then `python/plan_scout.py:512-516` calls `_emit_kv("WARN", warning)` without sanitizing it. A scout response with an invalid name like `bad\nname` plus a valid archetype raises `ValueError` before `_write_manifest()` and `SCOUT_STATUS`, dropping valid archetypes and forcing validation-failed/static fallback.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Sanitize warnings before emitting, matching `filter_plan_manifest()`, or write the filtered manifest before warning emission and ensure warning emission cannot abort the scout result.


### FINDING_13: persist-retally-step3-env.sh aborts on retally-handoff UsageError
- **Reviewer(s)**: dyn-shell-callsite-output.txt
- **Severity**: important
- **Concern**: `scope-anchor retally-handoff` runs inside command substitution under `set -euo pipefail`. The deleted `larch_scope_anchor_retally_handoff_value` always exited 0 (empty handoff on relay failure or invalid paths). The Python CLI returns exit **2** on `UsageError` (e.g. `validate_design_tmpdir` rejection). That aborts the whole persist step instead of yielding an empty handoff. MainAgent re-tally can lose `.step3-plan-review-result.env` / `.step3-review-result.env` refresh.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-callsite-output.txt: Guard the call (`set +e`, capture rc) and treat exit 2 like the old shell helper: empty `_scope_handoff`, optional `emit_kv WARN`, then continue env merge.


### FINDING_14: relay-allowed treats all non-zero exits as denial
- **Reviewer(s)**: dyn-shell-callsite-output.txt
- **Severity**: important
- **Concern**: `python3 … scope-anchor relay-allowed … || SCOPE_ANCHOR_FILE=""` in `run-step3-review.sh:376` treats **any** non-zero CLI exit (missing `python3`, bad `PLUGIN_ROOT`, argparse failure) the same as relay-gate denial. The in-process `larch_scope_anchor_relay_allowed` only returned 0/1. Operators get silent scope-anchor loss with no `execution-issues.md` breadcrumb distinguishing infra failure from policy.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-callsite-output.txt: Capture exit code separately; clear `SCOPE_ANCHOR_FILE` only on exit 1; on exit 2 emit `WARN` (and optionally append to `execution-issues.md`) before clearing or aborting.


### FINDING_4: malformed ndjson crashes dispatch/aggregate
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Malformed ndjson in panel manifest paths crashes dispatch/aggregate instead of emitting failed status. A corrupted `panel-outputs.ndjson` or `decompose-slots.ndjson` line causes uncaught `JSONDecodeError`; Step 2b.5 aborts without `PANEL_STATUS`/`AGGREGATOR_STATUS` KVs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Catch JSONDecodeError per line; emit panel-failed/failed KVs and exit 2 like the bash contract


