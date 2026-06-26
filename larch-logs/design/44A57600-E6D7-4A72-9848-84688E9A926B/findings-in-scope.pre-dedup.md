### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/lint_env_via_config_constant.py:165-169
- **Concern**: Env Baseline subsection still lists only three fields while identity requires six plus reason. Scenario: Prior round fix is incomplete: required keys still show only env_name, constant, and access. load_baseline can accept three-field rows while matching and --write need file, qualified_symbol, occurrence, and non-empty reason, causing cross-symbol collapse, unstable keys, or reasonless grandfather rows
- **Proposed resolution**: Mirror the subprocess Baseline block: exact required key frozenset (file, qualified_symbol, env_name, constant, access, occurrence, reason), unknown-key rejection, canonical sort, --write structural regen with reason preservation, --initial-reason bootstrap, and missing-reason exit 2



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/lint_env_via_config_constant.py:134-141
- **Concern**: Env linter module still lacks an explicit Scope block matching subprocess. Scenario: Only an orphaned config.py exclusion and a normalization bullet appear under the module heading. Without recursive python/**/*.py enumeration, symlink skip, test_*.py skip, and helper filename exclusions (conftest.py, test_support.py, review_test_support.py), an implementer can copy lint_keyword_only.iter_source_files top-level glob and miss nested production modules or scan harness files subprocess already excludes
- **Proposed resolution**: Add a **Scope:** subsection parallel to subprocess: recursive production scan, POSIX file paths relative to python/, skip symlinks, exclude config.py only, skip test_*.py at any depth, skip the same helper filenames, and state that scan uses the recursive enumerator rather than glob("*.py")



### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/lint_env_via_config_constant.py:160-162
- **Concern**: Env occurrence rules in the module section still omit subprocess-parity lexical pre-order and pre-suppression numbering. Scenario: The env module still says source order only. It never requires lexical pre-order over node.body (not ast.walk) or numbering all matching sites before pragma, exemption, or baseline filtering. Traversal or suppression order can attach the wrong occurrence ordinal and churn baseline keys
- **Proposed resolution**: Copy the subprocess Occurrence identity bullets into the env module: lexical pre-order over node.body, compute occurrence before suppression layers, and state that pragma or exemptions suppress reporting only without renumbering siblings



### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/test_lint_env_via_config_constant.py:203-226
- **Concern**: Env pytest list still omits ratchet and fail-closed cases required by Testing strategy acceptance. Scenario: The env test bullets stop at happy-path detection and some exemption cases. They omit subprocess-parity cases acceptance explicitly requires: baselined warn-only vs new-live exit 1, blank or missing baseline reason exit 2, --write reason preservation and missing-reason exit 2, malformed baseline or exemptions JSON exit 2, exemption rows with missing or empty file or reason or unknown keys, and syntax-error handling parity with lint_keyword_only
- **Proposed resolution**: Extend python/test_lint_env_via_config_constant.py bullets to mirror python/test_lint_subprocess_via_runner.py lines 120-132 plus acceptance checks at plan lines 343-349 so env-only bootstrap, load, and --write failure paths cannot ship untested



### FINDING_5:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/lint_env_via_config_constant.py:184-185
- **Concern**: Env Output subsection omits warn-for-baselined versus fail-for-new-live behavior. Scenario: Subprocess documents warn for baselined findings and fail only for live findings in its Output block. The env module Output bullet only lists message fields, so implementers may treat grandfathered env debt as silent pass or fail the whole run on baselined rows
- **Proposed resolution**: Add an **Output:** subsection matching subprocess: warn for baselined findings, fail only for live findings absent from baseline and exemptions, and reference shared exit 0/1/2 semantics from Approach



### FINDING_6:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:56-69
- **Concern**: Subprocess baseline load still omits structural value validation. Scenario: A malformed baseline row with empty file or qualified_symbol would load successfully, then never match live findings or preserve reasons, so the ratchet can drift silently.
- **Proposed resolution**: Validate non-empty POSIX-relative file and non-empty qualified_symbol on load, matching the existing ratchet pattern before comparing or writing.



### FINDING_7:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:165-169,202-226
- **Concern**: Env baseline schema still does not spell out the full identity tuple or structural validation. Scenario: The plan still treats env rows as env_name/constant/access entries, but the ratchet key also depends on file, qualified_symbol, and occurrence. An implementer can accept structurally bad rows or collapse distinct symbols, breaking --write preservation and baseline matching.
- **Proposed resolution**: Add the exact required env baseline record keys, reject missing or malformed structural fields on load, and add pytest coverage for those failures.



### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/lint_env_via_config_constant.py:164-169
- **Concern**: Prior-round env Baseline fix is still incomplete versus subprocess parity. Scenario: The env module Baseline bullets still list only env_name, constant, and access. They omit file, qualified_symbol, occurrence, and non-empty reason as required keys, plus exact-key frozenset validation, canonical sort, load_baseline fail-closed rules, --write reason preservation, --initial-reason bootstrap, and missing-reason exit 2 that subprocess documents at lines 54-69.
- **Proposed resolution**: An implementer can ship load_baseline validating three fields while --write and ratchet matching need the full identity tuple, causing cross-symbol collapse, unstable keys, or reasonless grandfathered rows. Mirror the subprocess Baseline block verbatim for env: required keys file, qualified_symbol, env_name, constant, access, occurrence, reason; identity key (file, qualified_symbol, env_name, constant, access, occurrence); canonical sort; --write preserve reasons; --initial-reason; load_baseline rejects missing/extra/empty reason keys with exit 2.



### FINDING_9:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/lint_env_via_config_constant.py:137-141
- **Concern**: Prior-round env Scope fix is still incomplete versus subprocess. Scenario: The env linter module section has no **Scope:** block. It shows only a lone config.py exclusion and one normalization bullet. It never restates recursive python/**/*.py enumeration, symlink skip, test_*.py at any depth, or conftest.py / test_support.py / review_test_support.py exclusions that subprocess lists at lines 25-34 and that lint_keyword_only.py uses via is_exempt_path.
- **Proposed resolution**: Copying lint_keyword_only.iter_source_files (glob("*.py") top-level only) misses nested production modules such as python/analysis/codex_role_costs.py and may scan test-support helpers subprocess already excludes. Add a **Scope:** subsection matching subprocess: recursive python/**/*.py; POSIX file paths relative to python/; skip proc.py N/A; exclude only config.py; skip test_*.py at any depth and the three helper filenames; skip symlinks.



### FINDING_10:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/lint_env_via_config_constant.py:160-162
- **Concern**: Prior-round env occurrence contract still lacks subprocess lexical pre-order rules. Scenario: Env occurrence text still says source order only. It never requires lexical pre-order over node.body (not ast.walk), numbering all matching sites before pragma/exemption filtering, with suppression not renumbering siblings, as subprocess specifies at lines 49-52.
- **Proposed resolution**: Traversal quirks or post-suppression renumbering can attach the wrong ordinal to a live env access, churn baseline keys, or attach grandfathered reasons to the wrong site. Copy subprocess Occurrence identity bullets into the env module: lexical pre-order over node.body, compute occurrence before pragma/exemption/baseline filtering, suppression does not renumber siblings.



### FINDING_11:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/test_lint_env_via_config_constant.py:203-226
- **Concern**: Prior-round env pytest ratchet parity list is still incomplete versus subprocess and Testing strategy acceptance. Scenario: The env pytest bullet list still stops at happy-path detection and scoped exemptions. It omits subprocess-parity cases required at plan lines 343-349: baselined warn-only vs new-live exit 1, blank/missing baseline reason exit 2, --write reason preservation and missing-reason exit 2, malformed baseline/exemptions JSON exit 2, and exemption rows with missing/empty file or reason or unknown keys.
- **Proposed resolution**: Env-only bootstrap, load, --write, and ratchet failure paths can ship untested while subprocess coverage at lines 120-131 is explicit and acceptance checks claim parity. Add the missing pytest bullets mirroring python/test_lint_subprocess_via_runner.py lines 120-131, including helper-filename skip fixtures if not covered elsewhere.



### FINDING_12:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/lint_env_via_config_constant.py:183-184
- **Concern**: Env module still lacks explicit warn-vs-fail Output contract subprocess documents. Scenario: Subprocess has an **Output:** subsection (lines 84-87) stating warn for baselined findings and fail only for new live violations. The env module ends with a field-list bullet only; warn/fail exit semantics live only in the shared Approach mirror and Testing strategy acceptance.
- **Proposed resolution**: Implementers may treat grandfathered env debt as silent pass or fail the whole run on baselined rows, diverging from keyword-only and subprocess ratchet behavior operators expect from make py-lint-main. Add **Output:** matching subprocess: warn for baselined findings; fail only for live findings absent from baseline and exemptions; exit 0 vs 1 vs 2 aligned with Approach.



### FINDING_13:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/lint_subprocess_via_runner.py:54-69
- **Concern**: Duplicate live and baseline identity checks are missing for the `(file, qualified_symbol, callee, occurrence)` key.. Scenario: A malformed baseline or a collector bug that emits the same subprocess call site twice can silently drop one row or misapply a reason instead of aborting.
- **Proposed resolution**: Reject duplicate live rows before write or check, and reject duplicate baseline rows on load, matching `lint_complexity_baseline.py`.



### FINDING_14:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/lint_env_via_config_constant.py:165-174
- **Concern**: Duplicate live and baseline identity checks are missing for the `(file, qualified_symbol, env_name, constant, access, occurrence)` key.. Scenario: A malformed baseline or collector bug can silently collapse two env findings that share the same identity, hiding or misattributing a ratchet row.
- **Proposed resolution**: Reject duplicate live rows before write or check, and reject duplicate baseline rows on load, matching `lint_complexity_baseline.py`.



### FINDING_15:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/lint_env_via_config_constant.py:165-169
- **Concern**: Env baseline subsection still lists only env_name, constant, and access as baseline fields while the identity tuple requires file, qualified_symbol, occurrence, and non-empty reason.. Scenario: load_baseline can validate three fields while --write and ratchet matching need the full tuple, causing cross-symbol collapse, unstable keys, reasonless grandfathered rows, or exit-2 gaps on bootstrap.
- **Proposed resolution**: Mirror the subprocess Baseline block: required exact keys file, qualified_symbol, env_name, constant, access, occurrence, reason; identity key minus reason; canonical sort; --write reason preservation; --initial-reason bootstrap; missing-reason exit 2; load_baseline rejects missing/extra keys and empty reason.



### FINDING_16:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/lint_env_via_config_constant.py:138-141
- **Concern**: Env linter module section still lacks an explicit Scope block matching subprocess (recursive python/**/*.py scan, POSIX file paths relative to python/, symlink skip, test_*.py and helper filename exclusions).. Scenario: Only config.py appears under the module heading. Copying lint_keyword_only.iter_source_files glob("*.py") can miss nested production modules such as python/analysis/*.py or scan test-support paths subprocess already excludes.
- **Proposed resolution**: Add a **Scope:** subsection mirroring subprocess: recursive enumeration, POSIX normalization, skip symlinks, exclude proc.py N/A, exclude config.py only, skip test_*.py at any depth, skip conftest.py/test_support.py/review_test_support.py.



### FINDING_17:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/lint_env_via_config_constant.py:160-162
- **Concern**: Env occurrence rules still say source order only and omit subprocess-parity lexical pre-order and pre-suppression numbering contract.. Scenario: Edge cases mention lexical pre-order globally but the env module text does not require walking node.body in declaration order (not ast.walk) or assigning occurrence before pragma/exemption filtering. Traversal quirks can attach the wrong ordinal, renumber siblings, or churn baseline keys.
- **Proposed resolution**: Extend the env Occurrence identity block to match subprocess lines 49-52: lexical pre-order over node.body, no ast.walk, compute occurrence before pragma/exemption/baseline filtering; suppressions do not renumber siblings.



### FINDING_18:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/test_lint_env_via_config_constant.py:202-226
- **Concern**: Env pytest bullet list still omits ratchet and fail-closed cases that subprocess lists and Testing strategy acceptance requires for parity.. Scenario: Happy-path detection is specified but baselined warn-only vs new-live exit 1, blank/missing baseline reason exit 2, --write reason preservation and missing-reason exit 2, malformed baseline/exemptions JSON exit 2, and exemption rows with missing/empty file or reason or unknown keys are absent. Env-only bootstrap, load, and --write failure paths can ship untested.
- **Proposed resolution**: Add subprocess-parity bullets: baselined warnings with exit 0 vs new violation exit 1; baseline blank/missing reason exit 2; --write preserves reasons and fails without --initial-reason; malformed baseline/exemptions JSON exit 2; exemption rows missing/empty file or reason or unknown keys exit 2.



### FINDING_19:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: plan.txt:165-170,186-193
- **Concern**: Env baseline schema still omits required record fields and non-empty reason validation. Scenario: The ratchet can collapse distinct findings, accept reasonless rows, and make --write reloads nondeterministic or silently corrupt
- **Proposed resolution**: Spell out file, qualified_symbol, env_name, constant, access, occurrence, and non-empty reason as required baseline keys, and add explicit load/write rejection rules



### FINDING_20:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:202-226
- **Concern**: Env pytest plan still omits explicit ratchet and fail-closed cases. Scenario: The new linter can ship without tests for baseline warn-vs-fail, missing or empty reason rejection, --write reason preservation, malformed JSON, and new-live exit 1
- **Proposed resolution**: Add explicit pytest bullets for those env ratchet and load/write failure paths, mirroring the subprocess coverage list



### FINDING_21:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: plan.txt:165-169
- **Concern**: Env Baseline subsection still lists only env_name, constant, and access as required record fields; prior-round fix incomplete.. Scenario: The identity tuple and Failure modes require file, qualified_symbol, occurrence, and non-empty reason, but the env module block never states the exact required-key frozenset, unknown-key rejection, canonical sort, load_baseline fail-closed rules, --write reason preservation, --initial-reason bootstrap, or missing-reason exit 2 that subprocess documents at plan.txt:57-69.
- **Proposed resolution**: Expand the env Baseline block to mirror subprocess: required keys file, qualified_symbol, env_name, constant, access, occurrence, reason; identity key; canonical sort; load_baseline rejects missing/extra/empty reason; --write preserves reasons; --initial-reason bootstrap; missing-reason exit 2.



### FINDING_22:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:138-141
- **Concern**: Env linter module still lacks an explicit Scope subsection matching subprocess; prior-round fix incomplete.. Scenario: Only config.py exclusion and a normalization bullet appear. Without recursive python/**/*.py enumeration, POSIX file paths, symlink skip, test_*.py at any depth, and helper filename exclusions (conftest.py, test_support.py, review_test_support.py), an implementer can copy lint_keyword_only.iter_source_files (python/*.py only) and miss nested production modules such as python/analysis/*.py.
- **Proposed resolution**: Add a **Scope:** block under python/lint_env_via_config_constant.py mirroring subprocess: recursive production scan, POSIX paths relative to python/, symlink skip, and the same depth-agnostic test/helper exclusions.



### FINDING_23:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:159-162
- **Concern**: Env occurrence rules omit subprocess-parity lexical pre-order and pre-suppression numbering; prior-round fix incomplete.. Scenario: The env module says source order only. It never requires lexical pre-order over node.body (not ast.walk) or computing occurrence before pragma/exemption filtering. Traversal quirks or suppression can attach the wrong ordinal and churn baseline keys.
- **Proposed resolution**: State the same occurrence contract as subprocess: lexical pre-order over node.body, count all matching sites before suppression, pragma/exemptions suppress reporting only and do not renumber siblings.



### FINDING_24:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/test_lint_env_via_config_constant.py
- **Concern**: Env pytest bullet list still omits ratchet and fail-closed cases required for subprocess parity; prior-round fix incomplete.. Scenario: The env test section stops at happy-path and scoped-exemption cases. It omits baselined warn-only vs new-live exit 1, blank/missing baseline reason exit 2, --write reason preservation and missing-reason exit 2, malformed baseline/exemptions JSON exit 2, and exemption rows with missing/empty file or reason or unknown keys even though Testing strategy acceptance (plan.txt:344-349) requires parity.
- **Proposed resolution**: Extend python/test_lint_env_via_config_constant.py bullets to match python/test_lint_subprocess_via_runner.py ratchet/fail-closed coverage line-for-line, adapted for env identity fields. **1. Env baseline contract (blocking, correctness)** — `plan.txt:165-169` still names only three baseline fields. Subprocess already documents the full ratchet loader at `plan.txt:57-69`. Without the same env prose, `load_baseline` can validate three fields while matching and `--write` need the full `(file, qualified_symbol, env_name, constant, access, occurrence)` tuple. **2. Env Scope (important, correctness)** — The env module has no **Scope:** block. `lint_keyword_only.iter_source_files` only globs top-level `python/*.py` (`python/lint_keyword_only.py:388-394`). Nested packages like `python/analysis/` would be skipped unless the plan states recursive enumeration explicitly, as subprocess does at `plan.txt:25-34`. **3. Env occurrence (important, correctness)** — Env occurrence text still says source order only. Subprocess requires lexical pre-order and pre-suppression numbering at `plan.txt:48-52`. Edge cases at `plan.txt:295-296` mention this but the implementer-facing module section does not. **4. Env pytest parity (important, risk-integration)** — `python/test_lint_subprocess_via_runner.py` bullets at `plan.txt:120-131` cover ratchet and fail-closed paths. The env test list at `plan.txt:202-226` does not, despite acceptance checks at `plan.txt:344-349`. Env-only bootstrap, load, and `--write` failure paths can ship untested.



### FINDING_25:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/lint_env_via_config_constant.py
- **Concern**: 1. Env baseline row shape is still not exact-set or fail-closed.. Scenario: The plan names the env baseline identity tuple, but it never says load must reject unknown keys or missing structural fields the way the subprocess linter does. A malformed row with a typo or extra field can still deserialize, which undermines ratchet fidelity and leaves the new acceptance criterion only partially specified.
- **Proposed resolution**: Define the env baseline required key set explicitly, reject unknown keys on load, and add pytest cases for missing and extra keys.



### FINDING_26:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/test_lint_subprocess_via_runner.py
- **Concern**: 2. Subprocess regression coverage omits the absent-baseline `--initial-reason` bootstrap path.. Scenario: The plan validates normal `--write` regeneration, but it never exercises the case the Makefile regen target depends on: baseline file absent and bootstrap reason supplied. That leaves a new baseline-creation path untested, so a regression there could ship while the listed tests still pass.
- **Proposed resolution**: Add a pytest that deletes the subprocess baseline file, runs `lint subprocess-via-runner --write --initial-reason ...`, and asserts bootstrap succeeds and writes canonical JSON.



