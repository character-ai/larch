### FINDING_1: Env baseline schema and load validation incomplete
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: blocking
- **Concern**: The env Baseline subsection (plan and `python/lint_env_via_config_constant.py`) still lists only `env_name`, `constant`, and `access` while the ratchet identity tuple requires `file`, `qualified_symbol`, `occurrence`, and a non-empty `reason`. Without the full required-key frozenset, unknown-key rejection, structural validation on load, canonical sort, `--write` reason preservation, `--initial-reason` bootstrap, and missing-reason exit 2, `load_baseline` can accept three-field or malformed rows while matching and `--write` need the full tuple. That can cause cross-symbol collapse, unstable keys, reasonless grandfathered rows, or silent ratchet drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Mirror the subprocess Baseline block: exact required key frozenset (file, qualified_symbol, env_name, constant, access, occurrence, reason), unknown-key rejection, canonical sort, --write structural regen with reason preservation, --initial-reason bootstrap, and missing-reason exit 2
  - From Codex-Arch: Add the exact required env baseline record keys, reject missing or malformed structural fields on load, and add pytest coverage for those failures.
  - From Cursor-Innovation: An implementer can ship load_baseline validating three fields while --write and ratchet matching need the full identity tuple, causing cross-symbol collapse, unstable keys, or reasonless grandfathered rows. Mirror the subprocess Baseline block verbatim for env: required keys file, qualified_symbol, env_name, constant, access, occurrence, reason; identity key (file, qualified_symbol, env_name, constant, access, occurrence); canonical sort; --write preserve reasons; --initial-reason; load_baseline rejects missing/extra/empty reason keys with exit 2.
  - From Cursor-Pragmatic: Mirror the subprocess Baseline block: required exact keys file, qualified_symbol, env_name, constant, access, occurrence, reason; identity key minus reason; canonical sort; --write reason preservation; --initial-reason bootstrap; missing-reason exit 2; load_baseline rejects missing/extra keys and empty reason.
  - From Codex-Pragmatic: Spell out file, qualified_symbol, env_name, constant, access, occurrence, and non-empty reason as required baseline keys, and add explicit load/write rejection rules
  - From Cursor-Requirements: Expand the env Baseline block to mirror subprocess: required keys file, qualified_symbol, env_name, constant, access, occurrence, reason; identity key; canonical sort; load_baseline rejects missing/extra/empty reason; --write preserves reasons; --initial-reason bootstrap; missing-reason exit 2.
  - From Codex-Requirements: Define the env baseline required key set explicitly, reject unknown keys on load, and add pytest cases for missing and extra keys.

### FINDING_2: Env Scope block missing subprocess parity
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The env linter module section lacks an explicit **Scope:** block matching subprocess. Only an orphaned `config.py` exclusion and a normalization bullet appear. Without recursive `python/**/*.py` enumeration, POSIX paths relative to `python/`, symlink skip, depth-agnostic `test_*.py` skip, and helper filename exclusions (`conftest.py`, `test_support.py`, `review_test_support.py`), an implementer can copy `lint_keyword_only.iter_source_files` top-level `glob("*.py")` and miss nested production modules or scan harness files subprocess already excludes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add a **Scope:** subsection parallel to subprocess: recursive production scan, POSIX file paths relative to python/, skip symlinks, exclude config.py only, skip test_*.py at any depth, skip the same helper filenames, and state that scan uses the recursive enumerator rather than glob("*.py")
  - From Cursor-Innovation: Copying lint_keyword_only.iter_source_files (glob("*.py") top-level only) misses nested production modules such as python/analysis/codex_role_costs.py and may scan test-support helpers subprocess already excludes. Add a **Scope:** subsection matching subprocess: recursive python/**/*.py; POSIX file paths relative to python/; skip proc.py N/A; exclude only config.py; skip test_*.py at any depth and the three helper filenames; skip symlinks.
  - From Cursor-Pragmatic: Add a **Scope:** subsection mirroring subprocess: recursive enumeration, POSIX normalization, skip symlinks, exclude proc.py N/A, exclude config.py only, skip test_*.py at any depth, skip conftest.py/test_support.py/review_test_support.py.
  - From Cursor-Requirements: Add a **Scope:** block under python/lint_env_via_config_constant.py mirroring subprocess: recursive production scan, POSIX paths relative to python/, symlink skip, and the same depth-agnostic test/helper exclusions.

### FINDING_3: Env occurrence rules omit lexical pre-order and pre-suppression numbering
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: Env occurrence rules still say source order only and omit subprocess-parity lexical pre-order over `node.body` (not `ast.walk`) and numbering all matching sites before pragma, exemption, or baseline filtering. Traversal or suppression order can attach the wrong occurrence ordinal, renumber siblings, or churn baseline keys.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Copy the subprocess Occurrence identity bullets into the env module: lexical pre-order over node.body, compute occurrence before suppression layers, and state that pragma or exemptions suppress reporting only without renumbering siblings
  - From Cursor-Innovation: Traversal quirks or post-suppression renumbering can attach the wrong ordinal to a live env access, churn baseline keys, or attach grandfathered reasons to the wrong site. Copy subprocess Occurrence identity bullets into the env module: lexical pre-order over node.body, compute occurrence before pragma/exemption/baseline filtering, suppression does not renumber siblings.
  - From Cursor-Pragmatic: Extend the env Occurrence identity block to match subprocess lines 49-52: lexical pre-order over node.body, no ast.walk, compute occurrence before pragma/exemption/baseline filtering; suppressions do not renumber siblings.
  - From Cursor-Requirements: State the same occurrence contract as subprocess: lexical pre-order over node.body, count all matching sites before suppression, pragma/exemptions suppress reporting only and do not renumber siblings.

### FINDING_4: Env pytest ratchet and fail-closed coverage incomplete
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The env pytest bullet list stops at happy-path detection and scoped exemptions. It omits subprocess-parity ratchet and fail-closed cases required by Testing strategy acceptance: baselined warn-only vs new-live exit 1, blank or missing baseline reason exit 2, `--write` reason preservation and missing-reason exit 2, malformed baseline or exemptions JSON exit 2, exemption rows with missing or empty file or reason or unknown keys, and syntax-error handling parity. Env-only bootstrap, load, and `--write` failure paths can ship untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend python/test_lint_env_via_config_constant.py bullets to mirror python/test_lint_subprocess_via_runner.py lines 120-132 plus acceptance checks at plan lines 343-349 so env-only bootstrap, load, and --write failure paths cannot ship untested
  - From Cursor-Innovation: Env-only bootstrap, load, --write, and ratchet failure paths can ship untested while subprocess coverage at lines 120-131 is explicit and acceptance checks claim parity. Add the missing pytest bullets mirroring python/test_lint_subprocess_via_runner.py lines 120-131, including helper-filename skip fixtures if not covered elsewhere.
  - From Cursor-Pragmatic: Add subprocess-parity bullets: baselined warnings with exit 0 vs new violation exit 1; baseline blank/missing reason exit 2; --write preserves reasons and fails without --initial-reason; malformed baseline/exemptions JSON exit 2; exemption rows missing/empty file or reason or unknown keys exit 2.
  - From Codex-Pragmatic: Add explicit pytest bullets for those env ratchet and load/write failure paths, mirroring the subprocess coverage list
  - From Cursor-Requirements: Extend python/test_lint_env_via_config_constant.py bullets to match python/test_lint_subprocess_via_runner.py ratchet/fail-closed coverage line-for-line, adapted for env identity fields. **1. Env baseline contract (blocking, correctness)** — `plan.txt:165-169` still names only three baseline fields. Subprocess already documents the full ratchet loader at `plan.txt:57-69`. Without the same env prose, `load_baseline` can validate three fields while matching and `--write` need the full `(file, qualified_symbol, env_name, constant, access, occurrence)` tuple. **2. Env Scope (important, correctness)** — The env module has no **Scope:** block. `lint_keyword_only.iter_source_files` only globs top-level `python/*.py` (`python/lint_keyword_only.py:388-394`). Nested packages like `python/analysis/` would be skipped unless the plan states recursive enumeration explicitly, as subprocess does at `plan.txt:25-34`. **3. Env occurrence (important, correctness)** — Env occurrence text still says source order only. Subprocess requires lexical pre-order and pre-suppression numbering at `plan.txt:48-52`. Edge cases at `plan.txt:295-296` mention this but the implementer-facing module section does not. **4. Env pytest parity (important, risk-integration)** — `python/test_lint_subprocess_via_runner.py` bullets at `plan.txt:120-131` cover ratchet and fail-closed paths. The env test list at `plan.txt:202-226` does not, despite acceptance checks at `plan.txt:344-349`. Env-only bootstrap, load, and `--write` failure paths can ship untested.

### FINDING_5: Env Output subsection omits warn-for-baselined vs fail-for-new-live
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: important
- **Concern**: The env module **Output** subsection only lists message fields and omits subprocess-parity warn-for-baselined versus fail-for-new-live behavior. Implementers may treat grandfathered env debt as silent pass or fail the whole run on baselined rows, diverging from keyword-only and subprocess ratchet behavior operators expect from `make py-lint-main`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add an **Output:** subsection matching subprocess: warn for baselined findings, fail only for live findings absent from baseline and exemptions, and reference shared exit 0/1/2 semantics from Approach
  - From Cursor-Innovation: Implementers may treat grandfathered env debt as silent pass or fail the whole run on baselined rows, diverging from keyword-only and subprocess ratchet behavior operators expect from make py-lint-main. Add **Output:** matching subprocess: warn for baselined findings; fail only for live findings absent from baseline and exemptions; exit 0 vs 1 vs 2 aligned with Approach.

### FINDING_6: Subprocess baseline load omits structural value validation
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: Subprocess baseline load still omits structural value validation. A malformed baseline row with empty `file` or `qualified_symbol` would load successfully, then never match live findings or preserve reasons, so the ratchet can drift silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Validate non-empty POSIX-relative file and non-empty qualified_symbol on load, matching the existing ratchet pattern before comparing or writing.

### FINDING_7: Subprocess duplicate live and baseline identity checks missing
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: Duplicate live and baseline identity checks are missing for the `(file, qualified_symbol, callee, occurrence)` key. A malformed baseline or a collector bug that emits the same subprocess call site twice can silently drop one row or misapply a reason instead of aborting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Reject duplicate live rows before write or check, and reject duplicate baseline rows on load, matching `lint_complexity_baseline.py`.

### FINDING_8: Env duplicate live and baseline identity checks missing
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: Duplicate live and baseline identity checks are missing for the `(file, qualified_symbol, env_name, constant, access, occurrence)` key. A malformed baseline or collector bug can silently collapse two env findings that share the same identity, hiding or misattributing a ratchet row.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Reject duplicate live rows before write or check, and reject duplicate baseline rows on load, matching `lint_complexity_baseline.py`.

### FINDING_9: Subprocess pytest omits absent-baseline `--initial-reason` bootstrap path
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: Subprocess regression coverage omits the absent-baseline `--initial-reason` bootstrap path. The plan validates normal `--write` regeneration but never exercises the case the Makefile regen target depends on: baseline file absent and bootstrap reason supplied. That leaves a new baseline-creation path untested, so a regression there could ship while the listed tests still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add a pytest that deletes the subprocess baseline file, runs `lint subprocess-via-runner --write --initial-reason ...`, and asserts bootstrap succeeds and writes canonical JSON.
