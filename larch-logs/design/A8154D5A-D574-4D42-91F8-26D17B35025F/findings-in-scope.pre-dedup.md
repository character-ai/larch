### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/review/review_dispatch_panel.py:1-3
- **Concern**: File-level comma-separated suppression grammars and baseline identity are underspecified. Scenario: The plan lists inline `# ruff: noqa: CODE - reason` and singular `# pyright: reportX=false # reason`, but production module headers use comma-separated lists without dash reasons, for example `# pyright: reportArgumentType=false, ...`, `# ruff: noqa: PLR2004,PTH105,ARG001,SIM103`, and `# pylint: disable=too-many-branches,...`. If the scanner splits on commas into per-code findings, each would need its own same-line reason and the ratchet would miss live suppressions or emit unfixable identities. Inline forms such as `# pyright: ignore[reportPrivateUsage,reportArgumentType]` in python/analysis/codex_role_costs.py:256 have the same risk.
- **Proposed resolution**: Add accepted file-header shapes `# ruff: noqa: CODE[, CODE...] # reason`, `# pyright: reportFlag=false[, reportFlag=false...] # reason`, and `# pylint: disable=check[, check...] # reason`. Pin baseline identity to one row per full normalized comment `text` (whole comma list), with one trailing `# reason` for the entire suppression. Document the same rule for bracket lists in `# type: ignore[...]` and `# pyright: ignore[...]`. Add pass/fail tests for comma-separated file headers and multi-code bracket ignores.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/tests/lint/test_lint_suppression_reason.py
- **Concern**: Following-line reason rejection lacks a negative test. Scenario: The plan requires same-line reasons and states file-level suppressions must not accept following comment lines, but the test list only covers adjacent preceding-line reasons. An implementation could accept a reason on the next line and still pass the listed suite, violating the v1 placement rule from the issue anchor.
- **Proposed resolution**: Add a failing fixture where the suppression is on one line and the reason is on the immediately following comment line; assert the scanner still reports a violation. ## Findings ### 1. architecture / correctness — `python/larch/review/review_dispatch_panel.py:1-3` The plan fixes prior scope gaps (`python/**/*.py`, `disable-next`, `skip-file`, shrink-on-write), but it still does not pin how comma-separated module-header suppressions are parsed or baselined. Production already uses headers like: # pyright: reportArgumentType=false, reportOptionalIterable=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportPrivateUsage=false, reportUnusedCallResult=false # ruff: noqa: PLR2004,PTH105,ARG001,SIM103 # pylint: disable=too-many-branches,too-many-statements,too-many-locals,too-many-arguments,unused-argument The accepted-shape list only documents inline dash forms for `noqa`/`ruff: noqa` and a singular `# pyright: reportX=false # reason`. It never defines the file-header `# reason` form for multi-code `ruff`/`pyright`/`pylint` lines, nor that the whole comment is one baseline identity. **Suggested revision:** Extend the grammar and baseline contract as in the TSV row above. ### 2. correctness — `python/tests/lint/test_lint_suppression_reason.py` The plan prose rejects following-line reasons, but the mandated tests only negate preceding-line reasons. That leaves a real v1 compliance hole on the feature’s own parsing path. **Suggested revision:** Add the negative following-line test described in the TSV row.



### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/issue/audit_runs.py:1-3
- **Concern**: Comma-separated single-tool directives lack a pinned one-identity rule. Scenario: Production file headers use one comment per tool with many comma-separated codes, e.g. `# pyright: reportUnusedCallResult=false, reportUnusedFunction=false` and `# ruff: noqa: ARG001, E701, ...`. The plan pins chained *different-tool* suppressions and occurrence-by-text, but not whether comma lists inside one `# pyright:` / `# ruff: noqa:` / `# pylint: disable=` span are one `text` identity with one shared reason. A per-code splitter would require impossible per-code reasons on a single physical line, miss live suppressions, or churn the baseline on harmless comma edits.
- **Proposed resolution**: Add an explicit rule and tests: one identity per matched tool directive (full comment-token text); comma-separated codes share one trailing `# reason` (pyright/pylint/type) or one `- reason` segment (noqa/ruff); add pass cases for comma pyright/ruff headers and a fail case if an implementer emits multiple rows from one header line.



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/tests/lint/test_lint_suppression_reason.py
- **Concern**: Following-line reason rejection lacks a plan-mandated negative test. Scenario: The plan now forbids following-line reasons for v1, but the acceptance list only requires a preceding-line negative test. An implementation that treats the next comment line as the reason would pass the listed tests while violating the stated same-line contract, letting new bare suppressions slip through when a reason sits on the line below.
- **Proposed resolution**: Add `Adjacent following-line reasons do not suppress a finding` to the required pytest cases, mirroring the existing preceding-line test. ## Findings ### 1. [correctness] Comma-separated single-tool directives lack a pinned one-identity rule **Location:** `python/larch/issue/audit_runs.py:1-3` (also `python/larch/core/architectural_guidelines.py:2-3`, `python/larch/review/review_dispatch_panel.py:1-3`) **Concern:** Round 1 flagged comma-separated file headers as OOS, but the revised plan still does not define how one physical comment line with many comma-separated codes maps to baseline `text` / `occurrence`. Production already relies on that shape heavily. **Suggested revision:** Pin one suppression identity per tool directive (entire comment token). Allow one shared trailing reason for the whole comma list. Add explicit pass/fail tests so a per-code splitter cannot ship. ### 2. [correctness] Following-line reason rejection lacks a plan-mandated negative test **Location:** `python/tests/lint/test_lint_suppression_reason.py` **Concern:** The plan text rejects following-line reasons, but only the preceding-line negative case is listed as required coverage. That leaves a realistic parser bug untested. **Suggested revision:** Add a following-line negative test to the plan’s mandatory test list. --- **Note on addressed prior items:** Scope (`python/**/*.py`), `disable-next`, `skip-file`, chained-suppression tests, `--write` shrink coverage, `always_run: true`, and the shrink test name are now in the plan. I did not re-raise those. **OOS not reported (ledger duplicates / low necessity):** shared `iter_source_files` import (OOS_1), custom `lint-*` pragmas (OOS_4), and `text` normalization details (rejected FINDING_7).



### FINDING_5:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: plan.txt:5-7,59-77
- **Concern**: [SCOPE-REDUCTION] Do not inherit the sibling lints' owner-module skips; keep the full production `python/**/*.py` scope in view.. Scenario: If the implementation copies `lint_subprocess_via_runner.iter_source_files` or `lint_env_via_config_constant.iter_source_files` verbatim, `python/larch/core/config.py:353` and any similar owner files stay outside the ratchet, so existing suppression debt and future bare suppressions there will still pass locally and in CI.
- **Proposed resolution**: Build a local iterator that only excludes tests, helper filenames, symlinks, cache, vendored, and virtualenv dirs. Do not carry over the `proc.py` or `config.py` self-exclusion from sibling lints.



### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/issue/audit_runs.py:1-3
- **Concern**: Comma-separated module-header suppressions are not pinned in grammar, identity, or tests. Scenario: The plan tests and accepted shapes use single-code examples (`# pyright: reportX=false`, `# ruff: noqa: CODE`, `# pylint: disable=check`), but production modules use multi-flag headers such as `python/larch/issue/audit_runs.py:1-3`, `python/larch/implement/ship.py:2-4`, and `python/larch/design/design_lifecycle.py:2-4`. A regex that only matches one flag/code can miss live suppressions entirely, so bare headers never enter the baseline and new ones pass cleanly. Splitting one header into per-code identities would also churn occurrence keys whenever a comma list changes.
- **Proposed resolution**: Add explicit rules that one comment token is one finding with `text` equal to the normalized full directive; cover fail/pass cases for comma-separated `# pyright: report…=false`, `# ruff: noqa: …`, and `# pylint: disable=…` headers; add a fixture based on a real header block and assert bootstrap emits one row per header comment.



### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/tests/lint/test_lint_suppression_reason.py
- **Concern**: Following-line reasons are required out but not negatively tested. Scenario: The plan forbids following-line reasons (`Do not accept preceding or following comment lines as reasons`) and tests preceding-line rejection, but the mandated test list omits a next-line reason case. An implementation could accept `# noqa: CODE` plus a reason on the next line and still satisfy the listed tests.
- **Proposed resolution**: Add one negative test: suppression on line N with reason text only on line N+1 must still fail.



### FINDING_8:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_suppression_reason.py
- **Concern**: Baseline identity includes the baseline row reason. Scenario: The live finding cannot carry the grandfathering reason from python/suppression-reason-baseline.json, so a literal reason-bearing identity either cannot match live findings or permits duplicate rows for the same suppression when only the reason differs. That breaks the required reason-preserving shrink baseline.
- **Proposed resolution**: Keep reason as a required record field, but exclude it from the matching, duplicate, stale-row, and write-preserve identity. Use file, suppression_kind, normalized text, and occurrence as the key.



### FINDING_9:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_suppression_reason.py
- **Concern**: Bare valid suppression forms are not pinned as violations. Scenario: The plan requires code-bearing accepted forms, but it does not require valid bare forms such as # noqa, # ruff: noqa, and # type: ignore to be reported. If the scanner only matches the accepted code-bearing regexes, a new unreasoned bare suppression can pass local lint and CI.
- **Proposed resolution**: Treat valid suppression-family comments that omit the required code or reason as violations, not plain comments. Add focused cases for bare noqa, ruff noqa, and type ignore.



### FINDING_10:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:31-39
- **Concern**: Baseline identity includes `reason`, but live findings cannot supply it. Scenario: Baseline duplicate, stale-row, and `--write` matching depend on comparing live findings to baseline rows. If `reason` is part of the identity, the lint can either fail to match live findings or allow two rows for the same suppression with different reasons, so the shrink-only baseline contract is not verifiable.
- **Proposed resolution**: Define the baseline identity as `file`, `suppression_kind`, `text`, and `occurrence`; keep `reason` as required validated metadata, not part of the matching key.



### FINDING_11:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:91-95
- **Concern**: Code/bracket-only matching can let valid bare suppressions bypass the lint. Scenario: A new `# noqa`, `# ruff: noqa`, `# type: ignore`, or `# pyright: ignore` is still a real suppression with no reason. If the scanner only recognizes the accepted code-specific reason forms, these broad unreasoned suppressions can pass locally and in CI.
- **Proposed resolution**: Add explicit violation handling and focused tests for bare valid suppression forms so unsupported broad suppressions fail rather than being treated as plain comments.



