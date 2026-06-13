# Review Round 1

- Mode: `diff`
- 8 accepted, 8 rejected (7 neutral)

## Accepted Findings

### FINDING_1: PRUNE_NITS_SH default points to missing prune script
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-review-cli-parity-output.txt
- **Severity**: important
- **Concern**: After relocating `review-core.sh` to `python/legacy_review_shell/`, the default `PRUNE_NITS_SH` still points at `$SCRIPT_DIR/prune-nit-findings.sh`, but `prune-nit-findings.sh` remains at `skills/review/scripts/prune-nit-findings.sh`. Review rounds that reach post-aggregate pruning get rc 127, fail open, and nit findings may reach voting unchanged.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Default to $PLUGIN_ROOT/skills/review/scripts/prune-nit-findings.sh and add pytest coverage for the prune stage
  - From codex-specialist-correctness-output.txt: Point the default to `$PLUGIN_ROOT/skills/review/scripts/prune-nit-findings.sh`, or port the prune boundary intentionally.
  - From cursor-specialist-edge-cases-output.txt: Set default to $PLUGIN_ROOT/skills/review/scripts/prune-nit-findings.sh and add integration test asserting prune runs
  - From codex-specialist-edge-cases-output.txt: Point the default to $PLUGIN_ROOT/skills/review/scripts/prune-nit-findings.sh or place the retained helper where review-core expects it.
  - From codex-specialist-testing-output.txt: Point the default at skills/review/scripts/prune-nit-findings.sh or the intended Python CLI surface, and cover the default path in tests.
  - From dyn-review-cli-parity-output.txt: Change the default to `$PLUGIN_ROOT/skills/review/scripts/prune-nit-findings.sh` (or copy/symlink the script into `legacy_review_shell` and keep the `$SCRIPT_DIR` default). Add a pytest that runs `review core` through the prune stage and asserts `prune-nit-findings.sh` is invoked successfully.


### FINDING_12: `.gitleaks.toml` allowlist still references deleted harness paths
- **Reviewer(s)**: dyn-retired-reference-sweep-output.txt
- **Severity**: important
- **Concern**: The allowlist `paths` array still references deleted harnesses `skills/review/scripts/test-review-core.sh` and `scripts/test-compose-review-findings.sh`, while the description was updated to `python/test_review_pipeline.py`. Those files no longer exist after the C1b cutover; the allowlist documents and protects wrong paths and leaves new pytest fixtures without explicit path entries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-retired-reference-sweep-output.txt: Replace lines 20 and 30 with `^python/test_review_pipeline\.py$` and `^python/test_compose_review\.py$` (or drop the retired entries if generic `python/*.py` coverage is sufficient), and keep the description and `paths` array in sync.


### FINDING_14: `test-prompt-template-invariants` contract table mismatches harness script
- **Reviewer(s)**: dyn-retired-reference-sweep-output.txt
- **Severity**: important
- **Concern**: `scripts/test-prompt-template-invariants.md:9` says the harness guards `python/review_pipeline.py`, but `scripts/test-prompt-template-invariants.sh:100-101` still copies and asserts against `python/legacy_review_shell/dispatch-panel.sh`. The mismatch hides the real prompt-owning surface from anyone using the `.md` contract or `docs/linting.md` cross-reference.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-retired-reference-sweep-output.txt: Update the markdown table to `python/legacy_review_shell/dispatch-panel.sh` (or retarget the shell harness to render/assert the live `review dispatch-panel` prompt fixture from Python, per the C1b plan).


### FINDING_15: `test-review-structure.sh` still greps legacy bash paths
- **Reviewer(s)**: dyn-retired-reference-sweep-output.txt
- **Severity**: important
- **Concern**: Sections 13, 16, and 17 in `scripts/test-review-structure.sh:310-370` still grep `python/legacy_review_shell/collect-findings.sh`, while failure messages refer to `collect-findings.sh` without the new path. Structural CI validates an archived bash copy, not the documented `review collect-findings` entrypoint, so drift between wrapper docs and legacy shell would not be caught under the names operators are directed to use.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-retired-reference-sweep-output.txt: Retarget greps to `python/review_pipeline.py` (for delegated behavior/docs) or to rendered CLI contract strings, and update fail messages to name `review collect-findings` / `python/review_pipeline.py`.


### FINDING_2: Makefile `test-dispatch-panel-core-dynamic` references nonexistent pytest path
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-review-cli-parity-output.txt, dyn-retired-reference-sweep-output.txt
- **Severity**: important
- **Concern**: `test-dispatch-panel-core-dynamic` invokes `pytest` on `python/test_review_pipeline.py-dynamic`, which is not a real file. `make test-dispatch-panel-core-dynamic` and harness shard 12 (`test-harnesses-12`) fail at collection, so former core-dynamic coverage is absent or blocked.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Fix pytest invocation to a real path/filter and add dynamic-scout pytest cases
  - From codex-specialist-correctness-output.txt: Change the target to `python/test_review_pipeline.py`, optionally with a valid `-k dynamic` selector if focused coverage is desired.
  - From codex-specialist-edge-cases-output.txt: Use a valid pytest file or a real -k selection.
  - From cursor-specialist-testing-output.txt: Use a valid pytest path or -k filter for the core-dynamic section
  - From codex-specialist-testing-output.txt: Use an existing pytest path or add the intended focused dynamic test file.
  - From dyn-review-cli-parity-output.txt: Point the target at a real pytest selector, e.g. `python3 -m pytest -q python/test_review_pipeline.py -k dynamic`, or add a dedicated test module if you want isolation.
  - From dyn-retired-reference-sweep-output.txt: Point the target at `python/test_review_pipeline.py` with a focused pytest selector (for example `-k core_dynamic` or a dedicated test class) matching the old `--section core-dynamic` coverage.


### FINDING_3: C1b review modules are bash shims, not planned Python ports
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-review-and-fix-handoff-output.txt
- **Severity**: important
- **Concern**: `python/review_pipeline.py`, `python/review_aggregate.py`, `python/review_tally.py`, and `python/compose_review.py` delegate to relocated bash under `python/legacy_review_shell/` via `run_legacy()` instead of providing importable Python implementations. Callers using `python3 python/cli.py review …` or importing tally helpers still execute legacy shell. Plan acceptance requiring deleted bash, direct CLI ownership, and testable Python logic is not met; runtime authority visible to operators (`python/cli.py review …`) diverges from the code that actually runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Implement planned Python stages or rescope; do not treat C1b as complete
  - From codex-specialist-correctness-output.txt: Port the listed shell bodies into the Python modules, keep only approved retained bash subprocess boundaries, and delete the legacy moved C1b shell entrypoints.
  - From codex-specialist-edge-cases-output.txt: Implement the C1b surfaces in Python, or keep the Bash scripts as explicit retained dependencies.
  - From codex-specialist-testing-output.txt: Implement the review pipeline surfaces in Python and delete the absorbed legacy shell runtime copies.
  - From dyn-review-and-fix-handoff-output.txt: Either finish the native port so `review core`/`compose-findings` are real Python implementations, or document and test the legacy delegation as the explicit contract (including a review-and-fix integration test that never stubs `REVIEW_CORE_CMD`).


### FINDING_4: Pytest harness replaces deleted bash coverage with thin smoke tests
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-review-cli-parity-output.txt
- **Severity**: important
- **Concern**: `python/test_review_pipeline.py` replaces ~5400 lines of deleted bash harness coverage with only a handful of smoke tests. Critical scenarios are unguarded: review-core stage ordering, prune-nit invocation, `cap-reached`, MAV handoff, OOS snapshot/restore, panel-failed, quiet-mode KV relay, scope-fit, security OOS, compose redaction, and ship-with-green-CI regressions including the broken `PRUNE_NITS_SH` default.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Port critical scenarios from deleted bash harnesses before deleting them
  - From cursor-specialist-testing-output.txt: Port deleted harness scenarios into pytest per plan matrices; add markers for Makefile sections
  - From dyn-review-cli-parity-output.txt: Port the highest-risk review-core contract tests from the deleted harnesses, at minimum: successful prune-nit subprocess, `REVIEW_CORE_STATUS=cap-reached` on round 5 with accepted findings, and quiet-mode KV capture through `run_legacy()`.


### FINDING_5: `relevant-checks.sh` missing focused harness routing for C1b modules
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-retired-reference-sweep-output.txt
- **Severity**: important
- **Concern**: `scripts/relevant-checks.sh` routes only `review_tally.py` to dedicated harnesses. Edits to `review_pipeline.py`, `review_aggregate.py`, `compose_review.py`, `python/test_review_pipeline.py`, or `python/legacy_review_shell/*` hit generic `py-lint` / `py-test` only, skipping retargeted Makefile harnesses (`test-gather-context`, `test-review-core`, `test-dispatch-panel-*`, `test-collect-findings`, `test-aggregate-findings`, `test-compose-review-findings`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add case arms for all new review Python modules and tests
  - From cursor-specialist-testing-output.txt: Add case arms and test-relevant-checks fixtures for all C1b Python modules
  - From dyn-retired-reference-sweep-output.txt: Add `case` arms mirroring the old bash mappings, for example `python/review_pipeline.py|python/test_review_pipeline.py|python/legacy_review_shell/*` → pipeline harness targets, `python/review_aggregate.py|python/test_review_aggregate.py` → `test-aggregate-findings`, and `python/compose_review.py|python/test_compose_review.py` → `test-compose-review-findings`.


