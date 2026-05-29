Reviewing the cited code to normalize and merge the reviewer findings accurately.
Merged five reviewer inputs into two findings: one waterfall tier-success contract (FINDING_1–3) and one test-harness gap for the removed 256 KB gate (FINDING_4–5).

### FINDING_1: Waterfall treats non-JSON `.raw` as tier success before validation
- **Reviewer(s)**: Cursor-Edge, unknown-slot, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The planned Codex→Claude waterfall defines tier success as exit 0 plus a non-empty `${OUTPUT}.raw`, before the existing `extract_valid_fenced_json` / `jq` validation runs. Any Codex-tier launcher that exits 0 while writing non-JSON prose (e.g. `launch-review.sh` `cap_hit` with `STATUS=cap_hit`, a harness `STUB_BIN/codex` that prints `codex review`, or similar) wins the waterfall and blocks the Claude tier. Downstream parse/validation then fails, yielding `SCOUT_STATUS=parse-failed` and zero archetypes even when Claude is available and tests expect `SCOUT_STATUS=ok`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Define tier success as exit 0 plus post-`extract_valid_fenced_json`/`jq` parseability, or on parse-failed retry the next tier when `--codex-present true` and Claude not yet tried
  - From unknown-slot: Define tier success as exit 0 plus parseable scout JSON (quick `jq`/`extract_valid_fenced_json` probe) or explicit launcher failure signals (`${raw}.cap-hit`, missing `${raw}.done` where applicable); on tier parse failure fall through to Claude. In `test-dispatch-panel.sh` dynamic cases stub `SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_REVIEW_SH` or pass `--codex-present false` unless Codex JSON is stubbed
  - From Cursor-Pragmatic: Define tier failure as exit non-zero, empty raw, `${raw}.cap-hit` present, or raw not JSON-shaped (e.g. no `{`); only then run Claude; in `test-dispatch-panel.sh` stub `SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_REVIEW_SH` to fail/empty for legacy dynamic scenarios or pass `--codex-present false` there

### FINDING_2: Plan drops 256 KB gate but leaves description-too-large harness expecting failure
- **Reviewer(s)**: Cursor-Requirements, Cursor-dyn-override-variable-isolation
- **Severity**: important
- **Concern**: The plan removes the `(( size <= 262144 ))` check from `validate_context_input_file` in `scripts/scout-dynamic-archetypes.sh` and adds a new large-diff success case, but does not update the existing `description-too-large` harness at `scripts/test-scout-dynamic-archetypes.sh:375-396`. That case still asserts exit 2 and stderr containing `exceeds 256 KB` for a ~270 KB `--description-file`. After the gate removal, the same input should be accepted (with staging) and succeed under the stub, so `make lint` fails unless the implementer discovers the conflict outside the plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: In scripts/test-scout-dynamic-archetypes.sh testing strategy: replace the description-too-large failure assertions with a success path (staged path in prompt, SCOUT_STATUS ok or empty per stub) or drop the case if redundant with the new large diff assertion; state this explicitly beside the >256 KB diff harness bullet
  - From Cursor-dyn-override-variable-isolation: Explicitly retarget or remove scripts/test-scout-dynamic-archetypes.sh:375-396 (e.g. assert a >256 KB --description-file is accepted/staged, or keep a separate inline --description-text argv cap test only)
