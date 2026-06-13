# Review Round 1

- Mode: `diff`
- 13 accepted, 4 rejected (4 neutral)

## Accepted Findings

### FINDING_1: scout_plan_archetypes remaps parse-failed to validation-failed
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `scout_plan_archetypes` maps `filter_plan_manifest` `parse-failed` to `validation-failed` on final `SCOUT_STATUS` emit. When the inner scout writes corrupt JSON but exits 0, `filter` returns `parse-failed` and the wrapper emits `validation-failed`, so consumers that gate on `parse-failed` mis-handle the failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Preserve parse-failed when filter_plan_manifest returns it; only use validation-failed for post-parse validation failures
  - From codex-specialist-testing-output.txt: Propagate parse-failed unchanged and add wrapper-level pytest coverage.


### FINDING_10: Missing decompose panel/aggregator pytest scenarios
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Pytest replaces deleted decompose panel/aggregator harnesses but omits degraded panel, `ALL_OUTPUT_FILES_PATH` partial-drop, both-tools-absent, and aggregator failure scenarios. Makefile decompose panel/aggregator targets pass while decomposition KV contract can regress silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Port deleted test-decompose-panel-dispatch.sh and test-decompose-aggregator.sh scenarios into test_decompose.py with stub waterfall scripts


### FINDING_17: relevant-checks mapping omits scope-anchor integration targets
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The `rendering.py` relevant-checks mapping omits required scope-anchor integration targets. Future scope-anchor edits can skip `test-dispatch-plan-voters` and `test-aggregate-findings`, missing voter/review validation regressions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Add test-dispatch-plan-voters and test-aggregate-findings to the python/rendering.py mapping.


### FINDING_18: scout_plan_archetypes changes ok to empty when filter removes all archetypes
- **Reviewer(s)**: dyn-migration-equivalence-output.txt
- **Severity**: important
- **Concern**: After a successful inner scout, `scout_plan_archetypes` emits `SCOUT_STATUS` from `filter_plan_manifest` (`empty` when the post-filter count is 0). The deleted `scout-plan-archetypes-wrapper.sh` kept the inner scout status and only updated `SCOUT_ARCHETYPE_COUNT`. When the inner scout returns `ok` but reserved-slug or cap filtering removes every archetype, shell emitted `SCOUT_STATUS=ok` with count `0`; Python emits `SCOUT_STATUS=empty`. Downstream surfaces that distinguish `ok` vs `empty` while still accepting a zero count can see different status even though the manifest is `{"archetypes":[]}`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-migration-equivalence-output.txt: After a successful filter, preserve the inner scout status when it is `ok` or `empty`, and derive only `SCOUT_ARCHETYPE_COUNT` from the filtered manifest (matching the shell wrapper contract).


### FINDING_2: Invalid scout JSON shape reported as empty instead of parse-failed
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Dynamic scout treats valid JSON with an invalid archetypes shape (for example `{}` or `{"archetypes":"bad"}` / `{"archetypes":{}}`) as empty instead of `parse-failed`. A scout subprocess that exits 0 with such output suppresses parse-failure diagnostics and is treated as a legitimate empty scout, so parse-failed gating and warnings are skipped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Emit parse-failed with invalid_archetypes_shape when the parsed JSON lacks an archetypes array.
  - From codex-specialist-edge-cases-output.txt: Treat non-empty parseable JSON with the wrong manifest shape as parse-failed, or run it through validate_dynamic_manifest before emitting empty.
  - From codex-specialist-testing-output.txt: Emit parse-failed with invalid_archetypes_shape for parsed JSON that lacks an archetypes array, and add pytest coverage.


### FINDING_21: test-lib-scope-anchor-handoff missing from test-harness shards (blocks lint)
- **Reviewer(s)**: dyn-docs-topology-output.txt
- **Severity**: important
- **Concern**: `Makefile:229` — `test-lib-scope-anchor-handoff` was added as a `.PHONY` recipe (pytest over `python/test_rendering.py`) but is not listed in any `test-harnesses-N` shard. `bash scripts/test-harness-shards-coverage.sh` fails with `missing from shards: test-lib-scope-anchor-handoff`, so `make lint` / `test-harnesses-15` cannot pass until this is fixed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-docs-topology-output.txt: Add `test-lib-scope-anchor-handoff` to an appropriate `test-harnesses-N` prerequisite list (for example `test-harnesses-7` alongside `test-persist-retally-step3-env` and `test-plan-review-scope-anchor`).


### FINDING_22: plan-review.md has contradictory scout ownership after C3c cutover
- **Reviewer(s)**: dyn-docs-topology-output.txt
- **Severity**: important
- **Concern**: Scout ownership is contradictory after the C3c cutover. The consumer paragraph (line 3) and "Dynamic plan-review archetypes" item 1 (lines 40–42) still describe Step 3 as invoking `python/cli.py scout plan-archetypes`, while "Single-pass review" (lines 54–57) and `skills/design/scripts/plan-review-loop.md:29` state review rounds consume Step 2b `scout-plan-manifest.json` and do not launch the scout per round. Maintainers following the top of `plan-review.md` may reintroduce per-round scout wiring.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-docs-topology-output.txt: Retarget the consumer paragraph and section 1 to Step 2b drafter ownership (`scout filter-manifest` / `scout plan-archetypes` at drafter time only); keep Step 3 prose limited to manifest consumption via `dispatch-plan-review-panel.sh`.


### FINDING_23: topology.tsv dynamic_archetypes authority points at stale doc
- **Reviewer(s)**: dyn-docs-topology-output.txt
- **Severity**: important
- **Concern**: `skills/shared/topology.tsv:3` / `docs/topology.md:13` — `design.plan_review.dynamic_archetypes` still lists `skills/design/references/plan-review.md` as runtime authority after scout logic moved to `python/plan_scout.py` (`python/cli.py scout plan-archetypes`, `scout dynamic-archetypes`, `scout filter-manifest`). The topology projection no longer points operators at the migrated implementation surface the plan names as authoritative.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-docs-topology-output.txt: Update the row's runtime authority to `python/plan_scout.py` (or `python/cli.py` with composition noting `scout *` verbs), extend `.claude/rules/topology-generation.md` `paths:` accordingly, and regenerate `docs/topology.md`.


### FINDING_25: SECURITY.md scope-anchor subsection not updated for Python cutover
- **Reviewer(s)**: dyn-docs-topology-output.txt
- **Severity**: important
- **Concern**: The plan required updating scope-anchor security prose for the Python cutover (`render scope-anchor` `DESIGN_TMPDIR` containment; `scope-anchor validate --mode review` with `--review-tmpdir`). The diff only retargets the dynamic-scout bullet (line 26) to `python/cli.py scout dynamic-archetypes`; the "Plan-review scope-anchor pipeline" subsection still describes staging/handoff behavior without naming `python/rendering.py`, `python/cli.py render scope-anchor`, or `python/cli.py scope-anchor validate`. Security and implementation docs diverge on where containment is enforced.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-docs-topology-output.txt: Extend the scope-anchor subsection to document the Python CLI verbs and their containment rules (design tmpdir for render/validate design mode; review tmpdir for review mode), matching `python/rendering.py` behavior.


### FINDING_26: SKILL.md Step 3 prose still implies per-round scout launch
- **Reviewer(s)**: dyn-docs-topology-output.txt
- **Severity**: important
- **Concern**: `skills/design/SKILL.md:527` — Step 3 prose still says "Scout, panel dispatch, collection, aggregation, voting, and tally run inside `plan-review-loop.sh`" while the same migration updated `plan-review-loop.md` to state the loop does not launch the plan scout per round. SKILL.md is the normative orchestration entrypoint; this sentence reintroduces the retired per-round scout mental model.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-docs-topology-output.txt: Split the sentence: panel/collect/aggregate/vote/tally remain in `plan-review-loop.sh`; scout/filter-manifest ownership belongs to Step 2b drafter launchers and `python/plan_scout.py`, with a cross-reference to `plan-review-loop.md`.


### FINDING_3: Integer-valued float JSON weights rejected (migration parity regression)
- **Reviewer(s)**: codex-specialist-correctness-output.txt, dyn-migration-equivalence-output.txt
- **Severity**: important
- **Concern**: `validate_dynamic_manifest` only accepts `weight` when `isinstance(weight, int)`, but the retired jq validator accepted any JSON number with a zero fractional part and stored `floor($a.weight)`. Models often emit whole-number weights as floats (`1.0`, `3.0`); those archetypes are now dropped with `invalid weight for <name>` instead of being capped and written, potentially removing all dynamic archetypes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Accept non-bool numeric weights whose value is integral, then cast to int.
  - From dyn-migration-equivalence-output.txt: Treat numeric weights as valid when they are whole numbers (for example `isinstance(weight, (int, float)) and not isinstance(weight, bool) and weight == int(weight)`), then persist `int(weight)` in the manifest.


### FINDING_4: Decompose waterfall pass-through KVs written to quieted stdout
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Waterfall pass-through KVs are written to quieted `sys.stdout` instead of the contract stream. The documented decompose panel-dispatch CLI omits `DISPATCH_OK` and `ALL_OUTPUT_FILES_PATH` from visible stdout under quiet init.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Replay dispatch_out through logging_util.emit or logging_util.contract_stream.


### FINDING_5: Scope-anchor validation does not reject unreadable files
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Scope-anchor validation does not reject unreadable regular files. A `chmod 000` anchor under `DESIGN_TMPDIR` can validate, then `render scope-anchor` raises `PermissionError` (or crashes) while reading it instead of failing closed cleanly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Check readability in _scope_anchor_common_shape_ok before accepting the path.
  - From codex-specialist-edge-cases-output.txt: Add a readability check by opening the file during common validation, and convert read failures into validation failure or UsageError.


