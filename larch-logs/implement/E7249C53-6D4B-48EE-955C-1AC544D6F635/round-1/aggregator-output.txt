Here is the normalized aggregator output. In-scope items are merged by shared behavioral risk; out-of-scope sources stay tagged and separate where concerns differ.

### FINDING_1: Regression test can green if file-level `LARCH_EXECUTION_ISSUES_LOG` unset is removed while inner `bash -c` still unsets before `exec`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: The leak/regression case runs `aggregate-findings` under a subprocess that unsets `LARCH_EXECUTION_ISSUES_LOG` before `exec`, so the SUT may not see a deliberately exported sentinel the way a top-level harness invocation would. Removing or weakening only the file-level unset prelude (e.g. lines 7–8) can still leave the case green while real harness shapes leak again; coverage is weaker than “inherited env visible to aggregate-findings” / plan step 4 wording implies unless supplemented (e.g. negative control without inner unset, whole-run guard, or documenting that the case pins only part of the contract).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Add a whole-script or no-inner-unset subprocess assertion that fails when entrypoint unset is removed, or document that this case only pins the duplicated prelude string.
  - From cursor-specialist-edge-cases-output.txt: Invoke AGG with env LARCH set and no inner unset plus assert artifacts under --review-tmpdir only, or spawn a subshell that only applies the harness entry unset (not a full inner prelude) so the test fails if entry unset is removed.

### FINDING_2: Sentinel/dispatch assertions do not prove `append_warning` wrote into execution-issues under `--review-tmpdir`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: The regression asserts an empty sentinel and `REASON=dispatch-failed` but not that `execution-issues` under `--review-tmpdir` received an aggregator warning line; `append_warning` could regress to a no-op while dispatch KV output still looks failed and the sentinel-oriented test still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_3: `CHANGELOG` may hide the harness fix from readers who only scan the dated release section
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: The harness fix is documented under Unreleased while the `42.0.3` section cites a different closed issue, so operators scanning only the dated `42.0.3` Changed bullets may miss the harness leak fix until the next release unless the note is mirrored or `#2617` is cited where the change actually ships.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_4: Duplicate env isolation unset/export blocks in `scripts/test-launch-review.sh` create maintenance noise and dual ownership
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt
- **Concern**: `LARCH_EXECUTION_ISSUES_LOG`, `SESSION_ENV_PATH`, and `IMPLEMENT_TMPDIR` are unset near script entry and again adjacent to the later `TMPROOT`-scoped unset/export block; redundancy increases the chance a future reorder drops one invariant or confuses which block owns isolation (no functional bug expected because the later block can re-establish the tmp-scoped log path).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Collapse to one unset+export sequence or drop the redundant first unset with a short comment at the surviving block.
  - From cursor-specialist-security-output.txt: Collapse to one unset block with a short comment if ordering matters.

### FINDING_5: Predictable `/tmp` sentinel path may be raceable via symlinks on shared multi-user hosts
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: A sentinel path under shared `/tmp` with a predictable PID suffix could be targeted by a co-user or local attacker racing symlink creation so writes intended for the sentinel follow an unexpected path if opens follow symlinks, weakening filesystem integrity assumptions on multi-user systems.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] Makefile `.PHONY` pruning vs retired test targets / external CI callers
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Retired test names were dropped from the mega-`.PHONY` line alongside a shard reshuffle; this is ancillary to `#2617` harness unset lines, but large pruning warrants verifying no external job still invokes removed `make` targets and that shard scripts no longer reference them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] Broad branch diff vs `#2617`-scoped review depth
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Multiple non-harness files change in the same diff versus `main`; review depth here was focused on `#2617` acceptance paths per plan, so unrelated hunks warrant normal PR split or per-file review rather than treating this pass as exhaustive for every path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] `aggregate-findings.sh` env-vs-flag precedence unchanged; future harnesses can still leak without unset prelude
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Environment can still win over `--review-tmpdir`; new harnesses can leak without an unset prelude; follow-up “Shape B” or a central env-sanitizer in a shared harness helper was explicitly deferred by plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_9: Plan fidelity vs full `merge-base(main)..HEAD` diff bundling multiple issues’ changes
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: The full branch diff bundles `#2616` cleanup, `larch-logs` flush, and `#2617` harness edits; most paths are absent from the `#2617` plan affected-files list and sequencing, so a strict plan-fidelity pass treating the whole diff as implementing only `#2617` can falsely read as incomplete or untraceable even when the `#2617` work matches its plan in isolation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_10: Plan step 4 prose vs implemented regression subprocess shape (`env` + child `unset` + `exec`)
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: The regression uses `env` plus a child `unset` plus `exec` rather than “export then invoke SUT with sentinel set” as plan step 4 literal wording might suggest; behavior can still match documented Shape A intent, but operators treating step 4 as an exact procedure may expect a different test shape.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

Notes on merges (for voters, not extra findings): Original inputs **1**, **8**, **11**, and **13** were merged into **FINDING_1** (same blind spot: inner unset/exec decouples the case from file-level prelude). **2**, **3**, **9**, and **12** merged into **FINDING_4** (duplicate unset blocks). **6** and **14** merged into **FINDING_6** (both `[OUT_OF_SCOPE]` Makefile/.PHONY / retired-target CI hygiene). **4** stayed separate from **FINDING_1** because it targets a different failure mode (proving `append_warning` side effects in `execution-issues`, not only sentinel/env visibility). **10** stayed separate from **FINDING_1** because it is a distinct threat model (`/tmp` symlink races), not the same “test passes without entry unset” coverage gap.

Because there is at least one `### FINDING_N:` block, **`LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` must not appear** in this output.
