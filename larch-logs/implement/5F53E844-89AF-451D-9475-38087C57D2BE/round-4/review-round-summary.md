# Review Round 4

- Mode: `diff`
- 11 accepted, 5 rejected (3 neutral)

## Accepted Findings

### FINDING_1: collect-findings `.done` sentinel wait coverage missing in pytest
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-mandated and retired `test-collect-findings.sh` coverage for `.done` sentinel wait, timeout failure, redacted wait diagnostics, and multiline/TSV collection is absent after C1b cutover. `review-core` tests stub collect entirely, so Claude output parsed before `.done` sidecars arrive, partial/empty findings, or unredacted timeout leaks can regress without CI signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add pytest exercising review collect-findings with stub wait-for-reviewers success and timeout paths asserting exit code COLLECT_OK and redacted stderr.
  - From cursor-specialist-edge-cases-output.txt: Port the retired collect-findings harness cases to pytest, invoking python/cli.py review collect-findings through the façade.
  - From cursor-specialist-testing-output.txt: Add pytest driving review collect-findings with stubbed .done sentinels, timeout failure, and redacted diagnostics.


### FINDING_12: Deleted dispatch-panel bash harness scenarios not ported to pytest/Makefile
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Deleted `test-dispatch-panel.sh` scenarios are not ported. Reuse/limits Make targets run identical full pytest file; dispatch regressions in round-2+ Codex gating, scout parse-failed handling, invalid dynamic counts, or no-fallback drops can merge without per-shard `-k` filters that previously caught them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Port deleted test-dispatch-panel.sh section cases into pytest and restore per-shard -k filters on Make targets.


### FINDING_14: run_legacy() forces plugin-root cwd, breaking consumer-repo git operations
- **Reviewer(s)**: dyn-review-cli-parity-output.txt
- **Severity**: important
- **Concern**: `run_legacy()` always runs legacy review scripts with `cwd=str(_PLUGIN_ROOT)` (the larch plugin checkout), not the caller's working tree. That breaks every git-relative step when invoked from a consumer repo (`/review`, nested `/implement` Step 5). `gather-context` diff/description modes, dirty-tree checkpoint, and `git checkout --` recovery all operate on the wrong repository.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-review-cli-parity-output.txt: Stop forcing plugin-root cwd in `run_legacy()`; inherit `os.getcwd()` from the invoking process (or pass an explicit repo-root cwd from session env). Add a regression test that creates a temp consumer git repo, makes a unique commit there, runs `review gather-context --mode diff`, and asserts the emitted `DIFF_FILE` content matches that repo rather than the plugin tree.


### FINDING_15: gather-context diff test does not assert consumer-repo diff content
- **Reviewer(s)**: dyn-review-cli-parity-output.txt
- **Severity**: important
- **Concern**: `test_gather_context_diff_mode_relays_branch_kvs_and_trailing_contract` sets `cwd=repo` on the pytest subprocess but does not assert gathered diff content comes from that repo. Because `run_legacy()` overrides cwd to `_PLUGIN_ROOT`, the test passes while the production cwd bug remains undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-review-cli-parity-output.txt: Extend the test to write a distinctive change in the temp repo, run `review gather-context --mode diff`, read the `DIFF_FILE` named in stdout, and assert it contains that change and not unrelated plugin-tree content.


### FINDING_17: topology panel_hard authority and rule paths mispointed after C1b cutover
- **Reviewer(s)**: dyn-retired-reference-sweep-output.txt
- **Severity**: important
- **Concern**: `implement.review_and_fix.panel_hard` runtime authority in `topology.tsv` was retargeted to `python/cli.py`, but hard-panel dispatch still runs through `python/review_pipeline.py` → `python/legacy_review_shell/dispatch-panel.sh`. `.claude/rules/topology-generation.md` replaced `dispatch-panel.sh` with catch-all `python/cli.py`, breaking the rule's own contract to extend `paths:` with each row's runtime authority. Topology consumers and path-triggered rules will miss panel edits or fire on unrelated CLI changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-retired-reference-sweep-output.txt: Set the authority to `python/review_pipeline.py` (or `python/legacy_review_shell/dispatch-panel.sh` if you want the prompt-owning shell surface) and regenerate `docs/topology.md`; add that same path to `.claude/rules/topology-generation.md` `paths:` so panel edits load the topology rule.
  - From dyn-retired-reference-sweep-output.txt: Swap `python/cli.py` for `python/review_pipeline.py` and `python/legacy_review_shell/dispatch-panel.sh` in `paths:` (drop the generic CLI entry unless another topology row truly needs it).


### FINDING_2: OOS snapshot/restore and parent OOS preservation untested
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-mandated OOS snapshot/restore tests are missing. Parent OOS files seeded under `SESSION_ENV_PATH`/`IMPLEMENT_TMPDIR` can be wiped on zero-findings or prune-skipped rounds without pytest guarding `review-core.sh` snapshot/restore behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add pytest that seeds parent oos-accepted-review.md and accumulated-oos.md runs review core through zero-findings and prune-skipped stubs and asserts parent files are restored verbatim.
  - From cursor-specialist-testing-output.txt: Add review-core pytest seeding parent OOS files with --session-env-path and asserting preservation.


### FINDING_21: review CLI verbs missing from _MACHINE_STDOUT_KEYS quiet-disable registry
- **Reviewer(s)**: dyn-review-and-fix-handoff-output.txt
- **Severity**: important
- **Concern**: `review core` and `review compose-findings` are not in `_MACHINE_STDOUT_KEYS`, so `cli.py` does not force `LARCH_QUIET_DISABLE=1` before dispatch. When quiet init is active, `run_legacy()` relays subprocess stdout through `logging_util.emit()` (fd 3), while `review-and-fix.sh` only redirects fd 1 into `review-core.env`, so `REVIEW_CORE_STATUS` and sibling KVs can be empty and Step 5 can mis-route as `unknown`. Today `review-and-fix.sh` defaults `LARCH_QUIET_DISABLE=1`, but that is caller-side coupling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-review-and-fix-handoff-output.txt: Register all machine-contract `review` verbs (`core`, `compose-findings`, `tally-code-votes`, `emit-tally`, etc.) in `_MACHINE_STDOUT_KEYS`, or make `run_legacy()` force quiet-disable and/or duplicate fd 3 onto stdout for KV consumers.


### FINDING_3: Parent rejected/OOS artifact handoff has no pytest equivalent
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The retired `test-review-core.sh` parent-copy test (`SESSION_ENV_PATH` → dirname copies for rejected/OOS artifacts) has no pytest equivalent. Nested `/implement` Step 5 can regress parent artifact handoff; fixes and OOS state would stay in the round tmpdir only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add a pytest that passes --session-env-path, runs a fix-required review core round, and asserts parent-dir rejected-findings.md and oos-accepted-review.md exist.


### FINDING_4: Deleted tally bash harness scenarios not fully ported to pytest
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-mandated and retired tally harness cases are incomplete in pytest: `--plan-file` scope-fit exemption, emit-tally OOS preservation, classification TSV, yield TSV, and degraded-voter paths. Misclassification, OOS sink loss, or tally/emit count divergence in nested `/implement` can ship without targeted failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add test with scope-files excluding a path that appears in --plan-file assert finding stays accepted and OUT_OF_SCOPE_DRIFT_COUNT stays 0.
  - From cursor-specialist-testing-output.txt: Port emit-tally preserve/rebuild/serialize scenarios into test_review_tally.py.
  - From cursor-specialist-testing-output.txt: Port deleted findings-classification and remaining tally harness scenarios into focused pytest.


### FINDING_7: plan-review-loop ignores aggregate-findings exit code and empty stdout
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: After CLI cutover, `aggregate-findings` exit code and empty stdout are ignored in `plan-review-loop.sh`. Empty `_agg_full` leaves `AGGREGATED=false REASON=ok`, so `AGGREGATOR_STATUS=ok` and plan-review votes on unmerged duplicate findings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Check aggregate-findings exit code and require AGGREGATED= KV in stdout before proceeding.


### FINDING_9: Aggregate pytest gaps (scope-anchor, waterfall, validation-exhausted)
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Scope-anchor-file, `DISPATCH_WATERFALL` override, validation-exhausted, invalid-anchor warnings, and `SESSION_ENV_PATH` failure-log pointer cases from the plan and retired bash harnesses are not present in pytest. Aggregator scope-anchor warnings, waterfall argv regressions, or exhausted validation can ship without targeted test failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add pytest cases for --scope-anchor-file invalid-file warning and AGGREGATE_DISPATCH_SH / DISPATCH_WATERFALL override behavior.
  - From cursor-specialist-testing-output.txt: Add pytest for validation-exhausted, --scope-anchor-file, invalid-anchor warnings, and SESSION_ENV_PATH failure-log pointers.


