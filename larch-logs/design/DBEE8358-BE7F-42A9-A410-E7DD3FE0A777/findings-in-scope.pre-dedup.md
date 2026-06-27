### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/lint_env_via_config_constant.py
- **Concern**: Prior-round env `_relocation_key` fix still incomplete: implementation bullets list only `env_name`, `constant`, `access` despite prose requiring a six-field relocation tuple. Scenario: An implementer following the `### UPDATED: python/lint_env_via_config_constant.py` bullets can build a 3-field key. Many distinct `IMPLEMENT_TMPDIR` rows in `larch/agents/agents.py` share the same env tuple across different `qualified_symbol` and `occurrence` values (confirmed in `env-via-config-constant-baseline.json`). Both baseline and live relocation counts exceed 1, `--write` raises `BaselineError`, and the packaging-move reason-preservation fix still fails.
- **Proposed resolution**: In the env linter `_relocation_key` bullets, enumerate all six relocation fields explicitly: `Path(file).name`, `qualified_symbol`, `env_name`, `constant`, `access`, `occurrence`. State that baseline and live counting both call the same helper on `Record` and `Finding` inputs.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_lint_env_via_config_constant.py
- **Concern**: Prior-round env package-move preservation test still lacks a named bootstrap-free contract. Scenario: Subprocess pins `test_write_preserves_reason_after_package_move_without_initial_reason` with `main(["--root", tmp, "--write"])` and no `--initial-reason`. The env test section still has orphan bullets (flat `agents.py` to `larch/agents/agents.py`, multi-row `qualified_symbol` preservation) under no function name. Implementers can satisfy the plan with only `test_write_fails_on_unmatched_env_finding_without_initial_reason` and skip the core relocated `--write` path.
- **Proposed resolution**: Add `test_write_preserves_reason_after_package_move_without_initial_reason` mirroring subprocess: flat-path multi-row baseline, live code under `larch/agents/agents.py`, `main(["--root", tmp, "--write"])` without `--initial-reason`, assert exit 0, package paths in rewritten baseline, and each distinct `qualified_symbol` keeps its original reason.



### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_lint_env_via_config_constant.py
- **Concern**: Prior-round bidirectional env ambiguity coverage still incomplete. Scenario: Round 1-4 accepted per-linter ambiguity tests for both collision directions. Subprocess names `test_write_fails_on_duplicate_old_rows_sharing_relocation_key` and `test_write_fails_on_duplicate_live_findings_sharing_relocation_key`, each asserting exit 2 without and with `--initial-reason`. The env test section documents only duplicate-old-baseline-rows and truncates before the one-old-row / two-live-findings case, test names, or exit contracts. Live-side relocation-key collisions on env `--write` can regress while the old-row test still passes.
- **Proposed resolution**: Name both env ambiguity tests to mirror subprocess. Cover duplicate-old and duplicate-live relocation-key collisions. Assert exit 2 on `--write` without `--initial-reason` and again with `--initial-reason` on each case.



### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:46-58
- **Concern**: 1) The env relocation-key contract is contradictory. The UPDATED section says the helper is a six-field tuple, but the enumerated fields only cover env_name, constant, and access.. Scenario: An implementer can follow the shorter list and still collapse distinct agents.py rows, which breaks package-move write preservation.
- **Proposed resolution**: Spell out Path(file).name, qualified_symbol, env_name, constant, access, and occurrence in the helper and count rules.



### FINDING_5:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:76-85
- **Concern**: 2) The env package-move preservation test still lacks an explicit bootstrap-free write contract.. Scenario: The test can pass while write still depends on --initial-reason, so a default-reason regression on relocated env rows would ship.
- **Proposed resolution**: Name the test and require main(["--root", tmp, "--write"]) without --initial-reason, mirroring the subprocess fixture.



### FINDING_6:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:86-87
- **Concern**: 3) The env ambiguity coverage still names only the duplicate-old-rows case.. Scenario: It omits the one-old-row / two-live-findings collision, so a live-side relocation-key conflict can still last-win or bootstrap through.
- **Proposed resolution**: Add the second named test for the live-side collision and assert exit 2.



### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/lint_env_via_config_constant.py
- **Concern**: Env `_relocation_key` implementation bullets still omit three of six required fields (prior rounds 3–4 accepted but incomplete). Scenario: The `### UPDATED: python/lint_env_via_config_constant.py` section calls for a six-field relocation tuple and later says counts use the full six-field tuple, but `_relocation_key` bullets list only `env_name`, `constant`, and `access`. An implementer following those bullets builds a too-broad key; many distinct `IMPLEMENT_TMPDIR` `get` rows in `larch/agents/agents.py` that share the env tuple but differ in `qualified_symbol` and `occurrence` collapse to one relocation key, per-side counts exceed 1, and `--write` raises `BaselineError` instead of preserving reasons after a package move.
- **Proposed resolution**: Expand `_relocation_key` bullets to enumerate all six fields: `Path(file).name`, `qualified_symbol`, `env_name`, `constant`, `access`, `occurrence`, matching the subprocess mirror and the plan's edge-case/failure-mode prose.



### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/test_lint_env_via_config_constant.py
- **Concern**: Env package-move preservation test still lacks a named bootstrap-free `--write` contract (prior rounds 2–4 accepted but incomplete). Scenario: The env test section has orphan bullets describing flat `agents.py` → `larch/agents/agents.py` multi-row preservation but no `test_write_preserves_reason_after_package_move_without_initial_reason` entry and no explicit `main(["--root", tmp, "--write"])` without `--initial-reason`. Subprocess already pins the analogue. Implementers can satisfy the plan with only `test_write_fails_on_unmatched_env_finding_without_initial_reason`, leaving the core packaging-move regression unverified.
- **Proposed resolution**: Add `test_write_preserves_reason_after_package_move_without_initial_reason` mirroring subprocess: flat-path multi-`qualified_symbol` baseline, live code under `larch/agents/agents.py`, `main(["--root", tmp, "--write"])` without `--initial-reason`, assert exit 0, package paths in baseline, and each row keeps its original reason.



### FINDING_9:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_lint_env_via_config_constant.py
- **Concern**: Env ambiguity coverage still omits duplicate-live collision, named tests, and fail-closed exit contract (prior rounds 1–4 accepted but incomplete). Scenario: Subprocess names `test_write_fails_on_duplicate_old_rows_sharing_relocation_key` and `test_write_fails_on_duplicate_live_findings_sharing_relocation_key`, each asserting exit 2 without and with `--initial-reason`. The env test section documents only the duplicate-old-baseline-rows case, omits one-old-row/two-live-findings, and lacks named tests or explicit exit-2 assertions. Live-side relocation-key collisions on env `--write` could regress while the old-row scenario still passes.
- **Proposed resolution**: Add both env ambiguity tests mirroring subprocess (duplicate-old and duplicate-live), each asserting exit 2 on `--write` without `--initial-reason` and again with `--initial-reason`. ### FINDING_1 — correctness — `python/lint_env_via_config_constant.py` Prior rounds 3–4 accepted that the env relocation key must match subprocess basename-plus-identity granularity. The plan’s edge cases and failure modes now say so, but the `_relocation_key` implementation bullets still list only `env_name`, `constant`, and `access`. Live `larch/agents/agents.py` baselines already contain many distinct `IMPLEMENT_TMPDIR` `get` rows differing by `qualified_symbol` and `occurrence`; a 3-field key collapses them and blocks `--write`. **Suggested revision:** List all six relocation fields in the implementation bullets. ### FINDING_2 — correctness — `python/test_lint_env_via_config_constant.py` Prior rounds 2–4 accepted a named env package-move write test without `--initial-reason`. The plan still has orphan fixture bullets under the env test section and no `test_write_preserves_reason_after_package_move_without_initial_reason` entry, while subprocess already names its analogue. **Suggested revision:** Add the named test with an explicit bootstrap-free `--write` invocation. ### FINDING_3 — correctness — `python/test_lint_env_via_config_constant.py` Prior rounds 1–4 accepted bidirectional ambiguity coverage per linter with fail-closed exit contracts. Subprocess specifies both collision directions and named tests. The env section still documents only duplicate-old baseline rows and omits duplicate-live findings, test names, and exit-2 assertions. **Suggested revision:** Mirror subprocess ambiguity test names and both collision directions, asserting exit 2 with and without `--initial-reason`. **Note:** Subprocess relocation spec and tests look complete relative to the issue scope. Optional check-mode relocation hints remain in the plan; prior rounds rejected dropping them as in-scope scope reduction, so they are not re-raised here.



### FINDING_10:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: plan.txt:49-55
- **Concern**: Env relocation key is under-specified. The bullet list only names env_name, constant, and access, but the plan also requires basename plus full semantic identity. That will collapse distinct agents.py rows that differ by Path(file).name, qualified_symbol, or occurrence.. Scenario: Package-move write can fail closed on real baselines, or reuse the wrong reason across collisions.
- **Proposed resolution**: Define the env relocation key as (Path(file).name, qualified_symbol, env_name, constant, access, occurrence) and count baseline/live rows on that full tuple.



### FINDING_11:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:76-80
- **Concern**: The env package-move preservation test is still only described as a multi-function fixture. It never pins a bootstrap-free --write run or a named test, so the moved-baseline preservation path can still be exercised only through --initial-reason.. Scenario: A default-reason regression on relocated package paths could slip through even though the test suite passes.
- **Proposed resolution**: Add test_write_preserves_reason_after_package_move_without_initial_reason and call main(["--root", tmp, "--write"]) with no --initial-reason.



### FINDING_12:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:86-87
- **Concern**: Env ambiguity coverage still stops after the duplicate-old-row shape. The one-old-row, two-live-findings case is omitted.. Scenario: Live-side relocation collisions could still regress while the old-row ambiguity test passes.
- **Proposed resolution**: Add the missing duplicate-live env collision test mirroring subprocess and assert exit 2 for that case.



### FINDING_13:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/lint_env_via_config_constant.py
- **Concern**: [INCOMPLETE PRIOR FIX] Env `_relocation_key` implementation bullets still list only three fields while adjacent text requires six. Scenario: The `### UPDATED: python/lint_env_via_config_constant.py` section says `_relocation_key` returns a full six-field tuple but the nested bullets list only `env_name`, `constant`, and `access`. Edge-case and failure-mode prose elsewhere requires `Path(file).name`, `qualified_symbol`, and `occurrence`. An implementer following the underspecified bullets builds a 3-field key; many distinct `IMPLEMENT_TMPDIR` `get` rows in `larch/agents/agents.py` that share the same env tuple across different `qualified_symbol` values collapse to one relocation key, per-side counts exceed 1, and `--write` raises `BaselineError` instead of preserving reasons after a package move.
- **Proposed resolution**: Rewrite the `_relocation_key` helper bullets to enumerate all six tuple fields explicitly: `Path(file).name`, `qualified_symbol`, `env_name`, `constant`, `access`, `occurrence`. Remove the contradictory 3-field list.



### FINDING_14:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/test_lint_env_via_config_constant.py
- **Concern**: [INCOMPLETE PRIOR FIX] Env package-move preservation test still lacks a named bootstrap-free contract. Scenario: Rounds 2–4 accepted mirroring subprocess with `test_write_preserves_reason_after_package_move_without_initial_reason` and `main(["--root", tmp, "--write"])` without `--initial-reason`. The env test section still has orphan bullets describing flat `agents.py` → `larch/agents/agents.py` multi-row preservation with no function name and no explicit write invocation. Subprocess already names its analogue. Implementers can satisfy the plan with only `test_write_fails_on_unmatched_env_finding_without_initial_reason`, leaving the core packaging-move regression unverified.
- **Proposed resolution**: Add `- Add test_write_preserves_reason_after_package_move_without_initial_reason:` with bullets: flat-path multi-function baseline under `agents.py`, live code under `larch/agents/agents.py`, `main(["--root", tmp, "--write"])` without `--initial-reason`, assert exit 0, assert package paths in rewritten baseline, and assert each distinct `qualified_symbol` keeps its original reason.



### FINDING_15:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_lint_env_via_config_constant.py
- **Concern**: [INCOMPLETE PRIOR FIX] Env ambiguity tests still omit duplicate-live collision and fail-closed exit contracts. Scenario: Round 1–4 accepted bidirectional ambiguity coverage per linter. Subprocess names `test_write_fails_on_duplicate_old_rows_sharing_relocation_key` and `test_write_fails_on_duplicate_live_findings_sharing_relocation_key`, each asserting exit 2 without and with `--initial-reason`. The env section says "Add two explicit ambiguity guard tests" but documents only the duplicate-old-baseline-rows case, omits the one-old-row / two-live-findings case, and lacks named tests or explicit exit-2 assertions (including that `--initial-reason` cannot bypass ambiguity). Live-side relocation-key collisions on env `--write` could regress silently.
- **Proposed resolution**: Mirror subprocess: add `test_write_fails_on_duplicate_old_rows_sharing_relocation_key` and `test_write_fails_on_duplicate_live_findings_sharing_relocation_key` with the same exit-2 without/with `--initial-reason` contract for both collision directions.



### FINDING_16:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: plan.txt:49-56
- **Concern**: Env relocation helper spec still omits `Path(file).name`, `qualified_symbol`, and `occurrence` even though the same plan says the env key must use all six fields.. Scenario: An implementation can follow the UPDATED bullet list literally and build a too-broad 3-field key, which will collapse distinct `agents.py` findings or fail to preserve package-move reasons after the `python/larch/agents/` move.
- **Proposed resolution**: Revise the UPDATED env bullet to spell out all six relocation-key fields, including `Path(file).name`, and make it match the failure-mode prose.



### FINDING_17:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:76-80
- **Concern**: Env package-move preservation coverage is still not pinned to a named test with an explicit bootstrap-free `--write` invocation.. Scenario: Implementers can satisfy the prose with an underspecified helper case and still miss the core regression: preserving reasons when `agents.py` moves to `larch/agents/agents.py` without `--initial-reason`.
- **Proposed resolution**: Add `test_write_preserves_reason_after_package_move_without_initial_reason` and explicitly require `main(["--root", tmp, "--write"])` with no `--initial-reason`.



### FINDING_18:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: plan.txt:86-88
- **Concern**: Env ambiguity coverage is truncated and still only names the duplicate-old-rows case.. Scenario: The live-side collision path, where one old row maps to two live findings, can still regress silently and `--initial-reason` could accidentally bootstrap colliding rows.
- **Proposed resolution**: Complete the env ambiguity tests with both collision directions and assert fail-closed exit-2 behavior before any `--initial-reason` fallback.



### FINDING_19:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/lint_env_via_config_constant.py
- **Concern**: Prior-round fix still incomplete: `_relocation_key` bullets list only three fields despite requiring a six-field tuple. Scenario: The env linter section calls for a full six-field relocation tuple and per-side counts built from it, but the `_relocation_key` bullets still name only `env_name`, `constant`, and `access`. Edge-case and failure-mode prose requires `Path(file).name`, `qualified_symbol`, and `occurrence`. An implementer following the bullets can build a 3-field key that collapses many distinct `IMPLEMENT_TMPDIR` rows in `larch/agents/agents.py`, triggering false `BaselineError` ambiguity and leaving package-move `--write` broken.
- **Proposed resolution**: Expand the `_relocation_key` bullets to the full tuple: `Path(file).name`, `qualified_symbol`, `env_name`, `constant`, `access`, `occurrence`, matching subprocess basename-plus-identity granularity.



### FINDING_20:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/test_lint_env_via_config_constant.py
- **Concern**: Prior-round fix still incomplete: env package-move preservation test lacks a named bootstrap-free `--write` contract. Scenario: Rounds 2–4 accepted mirroring subprocess with `test_write_preserves_reason_after_package_move_without_initial_reason`. The env test section still has orphan bullets (flat `agents.py` → `larch/agents/agents.py`, multi-`qualified_symbol` preservation) under no function name and no explicit `main(["--root", tmp, "--write"])` without `--initial-reason`. Implementers can satisfy the plan with only the unmatched-env test and ship a relocation regression on the core packaging-move path.
- **Proposed resolution**: Add `test_write_preserves_reason_after_package_move_without_initial_reason` with the orphan-bullet fixture, `main(["--root", tmp, "--write"])` (no `--initial-reason`), exit 0, package paths in baseline, and per-`qualified_symbol` reason preservation.



### FINDING_21:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_lint_env_via_config_constant.py
- **Concern**: Prior-round fix still incomplete: env ambiguity tests omit duplicate-live collision, names, and fail-closed exit contracts. Scenario: Round 1–4 accepted bidirectional ambiguity coverage per linter. Subprocess names `test_write_fails_on_duplicate_old_rows_sharing_relocation_key` and `test_write_fails_on_duplicate_live_findings_sharing_relocation_key`, each asserting exit 2 without and with `--initial-reason`. The env section promises two tests but documents only duplicate-old baseline rows, truncates mid-bullet, omits one-old/two-live-findings, and lacks named tests or exit-2 assertions. Live-side env relocation-key collisions could regress silently.
- **Proposed resolution**: Name both env ambiguity tests mirroring subprocess, add the one-old-row/two-live-findings fixture, and assert exit 2 on `--write` without and with `--initial-reason` for each collision direction.



### FINDING_22:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: plan.txt:46-56
- **Concern**: Env relocation key is under-specified in the UPDATED section. Scenario: The helper bullets only enumerate env_name, constant, and access. An implementer can omit Path(file).name, qualified_symbol, or occurrence and collapse distinct larch/agents/agents.py rows, which makes package-move write either fail on ambiguity or preserve the wrong reason.
- **Proposed resolution**: Spell out the six-field key in the UPDATED bullets and bind the per-side count and uniqueness rules to that full tuple.



### FINDING_23:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:76-80
- **Concern**: Env package-move preservation test is still only an orphan bullet. Scenario: The env section never names test_write_preserves_reason_after_package_move_without_initial_reason or requires main(["--root", tmp, "--write"]) without --initial-reason. A default-reason regression on the relocated agents.py fixture could ship while tests still pass.
- **Proposed resolution**: Add the named test and require the bootstrap-free write invocation plus preserved-reason assertions for each moved row.



### FINDING_24:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:86-87
- **Concern**: Env ambiguity coverage still omits the duplicate-live relocation case. Scenario: The env section sketches only the two-old-rows, one-live case and does not name the one-old, two-live collision or its explicit exit-2 assertions before and after --initial-reason. A live-side relocation-key collision could still regress or bootstrap differently without a test that fails closed.
- **Proposed resolution**: Add the duplicate-live test and make both ambiguity tests assert exit 2 without --initial-reason and again with it.



