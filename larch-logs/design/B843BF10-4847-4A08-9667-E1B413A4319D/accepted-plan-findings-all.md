### FINDING_1: Retired-script lint basename matching false-flags live analyze-issues scripts
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge, Cursor-dyn-consumer-sweep
- **Severity**: important
- **Concern**: The planned retired-scripts lint matches bare basenames such as `run-analysis.sh` / `run-analysis.md`, which collides with live analyze-issues files that legitimately use the same names. This would make `make lint-retired-scripts` fail on a clean tree unless unrelated live skill files are renamed or excluded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Seeding skills/report-tokens/scripts/run-analysis.sh makes basename run-analysis.sh a lint needle; tracked files under .claude/skills/analyze-issues/ (and test-analyze.sh comments) legitimately contain run-analysis.sh, so make lint-retired-scripts fails immediately and cannot be cleared without renaming unrelated scripts [SCOPE-REDUCTION] Scan content for full manifest paths only (or require a distinctive path prefix such as skills/report-tokens/scripts/); drop bare-basename matching from migration_lint.py and migrated-scripts.tsv header/playbook text
  - From Cursor-Edge: [SCOPE-REDUCTION] Match only full manifest paths (drop basename rule for F1), or add an explicit allowlist for live same-basename paths; extend `test_migration_lint.py` with a non-colliding live-basename fixture
  - From Cursor-dyn-consumer-sweep: Restrict matching to manifest full paths only, or exclude .claude/skills/analyze-issues/ from basename scans; do not require analyze-issues rewrites


### FINDING_2: Cutover sweep omits tracked retired report-tokens path references
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Edge, Codex-Innovation, Cursor-Requirements, Codex-dyn-consumer-sweep, Codex-dyn-quiet-dispatch-contract
- **Severity**: important
- **Concern**: The plan deletes or retires `skills/report-tokens/scripts/run-analysis.{sh,md}` and enables manifest lint, but omits tracked docs/rules that still reference those exact retired paths. Those stale references would either block `make lint` or leave broken operator documentation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add UPDATED rows for .claude/rules/gh-body-file.md and docs/installation-and-setup.md; rewrite setup_report_tokens_wrapper_repo and section 3j2 to touch skills/report-tokens/SKILL.md and expect py-test (not test-run-analysis-quiet)
  - From Codex-Arch: Add these docs to the update set: replace report-tokens wrapper contract references with cli.py report-tokens analyze / docs/python-migration.md, and rewrite active-driver invocation prose to python3 ${CLAUDE_PLUGIN_ROOT}/python/cli.py ship pr while preserving true module-role mentions of python/ship.py.
  - From Cursor-Edge: Add `docs/installation-and-setup.md` to the cutover sweep (point at `docs/python-migration.md` / `python/cli.py report-tokens analyze`)
  - From Codex-Innovation: Add these files to the cutover sweep and remove or repoint the stale report-tokens wrapper/doc references before enabling the manifest lint
  - From Cursor-Requirements: Add UPDATED docs/installation-and-setup.md: cli.py ship pr + report-tokens analyze invocations; relocate rate-override env docs to SKILL.md or python/README.md
  - From Codex-dyn-consumer-sweep: Add these docs to the UPDATED list and replace process-invocation text with python3 ${CLAUDE_PLUGIN_ROOT}/python/cli.py ship pr or the generic cli.py direct-call convention; move the rate-override pointer to the surviving report-tokens CLI/playbook docs.
  - From Codex-dyn-quiet-dispatch-contract: Update this doc as part of the stale-reference sweep, retargeting the rate-override pointer to a surviving report-tokens doc or moving that env-var reference before deleting run-analysis.md


### FINDING_3: Relevant-checks harness still embeds retired report-tokens paths and deleted target expectations
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge
- **Severity**: important
- **Concern**: `scripts/test-relevant-checks.sh` still fabricates the retired report-tokens wrapper/doc paths and expects the deleted `test-run-analysis-quiet` target. After the wrapper deletion and manifest lint, the harness source itself would contain lint-failing retired literals and stale target assertions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add UPDATED rows for .claude/rules/gh-body-file.md and docs/installation-and-setup.md; rewrite setup_report_tokens_wrapper_repo and section 3j2 to touch skills/report-tokens/SKILL.md and expect py-test (not test-run-analysis-quiet)
  - From Cursor-Edge: Rewrite section 3j2 to touch `skills/report-tokens/SKILL.md` or `python/migrated-scripts.tsv` and assert `py-test` / `lint-retired-scripts`; remove retired literals from harness source


### FINDING_5: Direct-call convention sweep misses docs still naming python/ship.py as invoked driver
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Cursor-Requirements, Codex-Requirements, Codex-dyn-consumer-sweep
- **Severity**: important
- **Concern**: Several canonical docs still describe `python/ship.py` as the default invoked Step 8+ driver even though the plan establishes direct `cli.py ship pr` invocation. This leaves stale user/operator guidance and undermines the direct-call convention.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add these docs to the update set: replace report-tokens wrapper contract references with cli.py report-tokens analyze / docs/python-migration.md, and rewrite active-driver invocation prose to python3 ${CLAUDE_PLUGIN_ROOT}/python/cli.py ship pr while preserving true module-role mentions of python/ship.py.
  - From Codex-Edge: Add a targeted update pass for these invocation-form references to python3 ${CLAUDE_PLUGIN_ROOT}/python/cli.py ship pr or cli.py ship pr, while leaving true module-role mentions of python/ship.py intact
  - From Cursor-Requirements: Add UPDATED docs/installation-and-setup.md: cli.py ship pr + report-tokens analyze invocations; relocate rate-override env docs to SKILL.md or python/README.md
  - From Codex-Requirements: Add these docs to the UPDATED list and change invocation/default-driver prose to python3 ${CLAUDE_PLUGIN_ROOT}/python/cli.py ship pr while preserving true module-role mentions of python/ship.py
  - From Codex-dyn-consumer-sweep: Add these docs to the UPDATED list and replace process-invocation text with python3 ${CLAUDE_PLUGIN_ROOT}/python/cli.py ship pr or the generic cli.py direct-call convention; move the rate-override pointer to the surviving report-tokens CLI/playbook docs.


### FINDING_6: Deleted report-tokens quiet wrapper behavior is not ported to direct CLI tests
- **Reviewer(s)**: Cursor-Edge, Codex-Requirements, Codex-dyn-quiet-dispatch-contract
- **Severity**: important
- **Concern**: The plan deletes the report-tokens quiet wrapper harness but only ports unrelated or insufficient fd-3 coverage. Without a direct `cli.py report-tokens analyze` subprocess test under staged quiet environment, regressions can hide the report body, cache trailer, or scan diagnostics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Add a `test_cli.py` subprocess case for `cli.py report-tokens analyze` under `LARCH_QUIET_ACTIVE=1` + foreign `LARCH_QUIET_PID` asserting `## Report Tokens Analysis` on captured stdout, or restore fds at the start of `report_tokens_cli.main` when a foreign quiet session is active
  - From Codex-Requirements: Add a subprocess pytest for python/cli.py report-tokens analyze --skill implement/design --no-issue --no-plot using synthetic larch-logs and staged quiet env, asserting the report and Cache JSON are visible on stdout and scan diagnostics remain visible as expected
  - From Codex-dyn-quiet-dispatch-contract: Add a python/test_cli.py subprocess case for cli.py report-tokens analyze under staged LARCH_QUIET_ACTIVE/LARCH_QUIET_PID that asserts stdout has Report Tokens Analysis and Cache JSON and stderr has Scanning, then delete the shell harness


### FINDING_7: docs/linting.md still lists deleted test-run-analysis-quiet target
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The plan removes the `test-run-analysis-quiet` harness but does not update linting documentation that still advertises the deleted make target.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Delete the test-run-analysis-quiet row in docs/linting.md; point quiet/fd-3 coverage to python/test_cli.py / make py-test


### FINDING_9:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:25-32; .claude/skills/analyze-issues/scripts/run-analysis.sh:14; .claude/skills/analyze-issues/SKILL.md:20,39
- **Concern**: [SCOPE-REDUCTION] Retired-script lint basename matching makes unrelated scripts with the same basename fail. Scenario: The manifest seeds run-analysis.sh and run-analysis.md; basename scanning will flag the still-live .claude analyze-issues run-analysis.sh docs and usage even though they are not the retired report-tokens wrapper, so make lint-retired-scripts cannot pass without out-of-scope edits
- **Proposed resolution**: Retarget lint to match full retired paths only, or make basename aliases explicit and do not seed non-unique run-analysis.* basenames


### FINDING_10:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/migration_lint.py:25-26
- **Concern**: [SCOPE-REDUCTION] Basename matching for retired paths collides with live analyze-issues script. Scenario: Manifest seeds skills/report-tokens/scripts/run-analysis.sh but migration_lint also flags basename run-analysis.sh; git-tracked .claude/skills/analyze-issues/scripts/run-analysis.sh and test-analyze.sh legitimately contain that string (~6+ files). make lint-retired-scripts fails on every PR after merge.
- **Proposed resolution**: Match manifest entries as full repo-relative paths only; drop basename scan from F1 or defer basename until analyze-issues renames its coordinator.


### FINDING_11:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:24-32
- **Concern**: [SCOPE-REDUCTION] Retired-script lint matches basenames across all tracked files. Scenario: The seeded basename run-analysis.sh is still a live, unrelated analyze-issues script name under .claude/skills/analyze-issues/SKILL.md:20 and .claude/skills/analyze-issues/scripts/run-analysis.sh:14, so the proposed lint either fails forever or forces unrelated renames outside F1
- **Proposed resolution**: Drop basename-only matching; match the manifest repo-relative paths and documented path spellings only, and update the planned tests/playbook to remove basename-only expectations


### FINDING_12:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/migration_lint.py:25-26
- **Concern**: [SCOPE-REDUCTION] Basename matching for retired paths will false-positive on unrelated tracked files that legitimately use the same filename. Scenario: The repo already ships `.claude/skills/analyze-issues/scripts/run-analysis.sh`, `run-analysis.md`, and multiple references to `run-analysis.sh` in `test-analyze.sh` / `SKILL.md`. Linting any occurrence of basename `run-analysis.sh` (and `run-analysis.md`) will fail `make lint-retired-scripts` even after the report-tokens sweep
- **Proposed resolution**: For F1, match only manifest full paths (drop basename rule) or require path-boundary / repo-relative matching; if basename stays, add an explicit exclusion carve-out is extra complexity—prefer full-path-only


### FINDING_13:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/migration_lint.py (proposed); .claude/skills/analyze-issues/SKILL.md:20-39; .claude/skills/analyze-issues/scripts/run-analysis.sh:14
- **Concern**: [SCOPE-REDUCTION] Retired-script lint matches every retired basename, not just retired paths. Scenario: The seeded basename run-analysis.sh is also a live analyze-issues script name, so make lint-retired-scripts would fail on unrelated tracked files or force unrelated renames/deletions outside this feature
- **Proposed resolution**: Match exact retired path strings only, or an anchored path suffix that includes the retired directory; remove basename-only matching from the lint, manifest docs, and tests


### FINDING_15:
- **Reviewer(s)**: Codex-dyn-consumer-sweep
- **Severity**: important
- **Focus area**: correctness
- **Location**: .claude/skills/analyze-issues/SKILL.md:20-39; .claude/skills/analyze-issues/scripts/run-analysis.sh:1-14; .claude/skills/analyze-issues/scripts/run-analysis.md:1-13
- **Concern**: [SCOPE-REDUCTION] Basename matching in the retired-scripts lint will flag unrelated analyze-issues files named run-analysis.sh and run-analysis.md. Scenario: The plan says migration_lint scans all tracked files and flags retired basenames. These tracked dev-skill files are not report-tokens consumers and are not being retired, so make lint-retired-scripts would fail unless the patch renames or rewrites unrelated out-of-scope analyze-issues surfaces.
- **Proposed resolution**: Change the lint rule to match full repo-relative retired paths only, or make basename matching conditional on basename uniqueness/explicit manifest opt-in, so unrelated same-name scripts are not treated as stale report-tokens references.




### FINDING_1: Retired-path literal ban must cover all tracked sources
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge
- **Severity**: important
- **Concern**: The planned retired-script lint scans all tracked files, but the no-literal testing rule is scoped too narrowly. New pytest/source files such as `python/test_migration_lint.py` could embed the seeded retired paths and cause permanent lint failures after the sweep lands.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend plan/testing strategy: all tracked pytest sources must use synthetic fixture paths only; never embed manifest seed paths in repo source
  - From Cursor-Edge: Extend the no-literal rule to all new/edited tracked sources (at minimum python/test_migration_lint.py; playbook step for pytest authors). Use synthetic retired paths inside fixture repos only, built at runtime from neutral segments or read from tmp manifest files—never the four seed manifest paths as literals in tracked source. Document the rule in docs/python-migration.md beside the matching-rule section.


### FINDING_2: Ship CLI cutover sweep misses stale `python/ship.py` direct-call guidance
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan removes or deprecates direct `python/ship.py` invocation without a complete consumer/prose sweep or lint coverage for that path. Residual guidance in implement surfaces or `SECURITY.md` could continue sending orchestrators/users to a dead or non-canonical entrypoint.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add explicit test-implement-structure.sh grep pins for NEVER #13 line 56 Step 8+ opener line 1049 and exit-matrix line 1147; require full-string cli.py ship pr replacement in same commit as __main__ removal
  - From Cursor-Pragmatic: Add SECURITY.md to the explicit consumer-cutover sweep: default-path prose should name python3 …/python/cli.py ship pr while keeping python/ship.py only for module-role references


### FINDING_3: Migration lint diagnostics can disappear after `quiet_init`
- **Reviewer(s)**: Codex-Arch, Codex-Pragmatic, Cursor-dyn-quiet-dispatch-ownership
- **Severity**: important
- **Concern**: The planned migration lint initializes quiet routing but still relies on caller-visible stderr diagnostics. Since `quiet_init()` redirects stdout/stderr to the quiet log, stale-reference findings, usage text, or manifest errors may be hidden from CI/pre-commit output unless routed through the original-stderr/breadcrumb path and tested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Route lint findings and usage/manifest errors through a Python larch_err equivalent or BreadcrumbWriter().emit after quiet_init, and add one failing lint subprocess test that asserts the file:line diagnostic is visible on stderr while KV stays on fd-3/stdout
  - From Codex-Pragmatic: Parse args before quiet_init; after quiet_init send lint diagnostics through BreadcrumbWriter or an explicit original-stderr helper; assert failing stale refs show file:line diagnostics on captured stderr
  - From Cursor-dyn-quiet-dispatch-ownership: Emit human-readable findings through logging_util.BreadcrumbWriter().emit() (fd 4 / lib-quiet parity) or document and implement an explicit non-quiet diagnostic path; add a subprocess test that quiet_init is active and a sample violation line is visible on captured stderr


### FINDING_5: Pytest subprocesses may resolve `python/cli.py` from the wrong cwd
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: Planned subprocess tests invoke repo-root-relative `python/cli.py`, but `make py-test` runs pytest from inside `python/`. Those commands can resolve to `python/python/cli.py` and fail even if the CLI works.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Derive the CLI path from Path(__file__).with_name("cli.py") or set subprocess cwd to the repo root before invoking python/cli.py


### FINDING_6: Relevant-checks cutover drops `docs/run-logs.md` report-tokens coverage
- **Reviewer(s)**: Cursor-dyn-sweep-completeness, Codex-dyn-sweep-completeness
- **Severity**: important
- **Concern**: The report-tokens relevant-checks rewrite replaces the deleted wrapper harness routing but omits the existing `docs/run-logs.md` trigger. Future run-log schema documentation edits could lose the report-tokens parity/pytest coverage they currently receive.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-sweep-completeness: Add docs/run-logs.md to the py-test case arm (with skills/report-tokens/SKILL.md and plot-cost-over-time.*) or give it an explicit successor target in the plan's scripts/relevant-checks.sh bullet
  - From Codex-dyn-sweep-completeness: Keep docs/run-logs.md in the new report-tokens relevant-checks arm and route it to py-test; update scripts/test-relevant-checks.sh without retired-path literals if a fixture needs to pin the preserved routing.


### FINDING_8:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/ship.py:1819-1820; python/report_tokens_cli.py:126-127
- **Concern**: [SCOPE-REDUCTION] Removing existing __main__ blocks is not required for the direct cli.py consumer cutover and turns old direct invocations into silent no-ops. Scenario: An existing caller still running python3 python/ship.py ... or python3 python/report_tokens_cli.py ... after this change exits 0 without running the driver/analyzer, which is worse than either supported compatibility or a loud deprecation failure
- **Proposed resolution**: Keep the existing __main__ blocks in F1 while cutting repo consumers to cli.py; if sole-entrypoint enforcement is required later, make old module execution fail loudly in a separate tracked change


### FINDING_9:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/ship.py:1819-1820; python/report_tokens_cli.py:126-127
- **Concern**: [SCOPE-REDUCTION] Removing the existing __main__ blocks is not required for the cli.py cutover and turns two current direct script entrypoints into silent no-op imports. Scenario: Existing documented/manual invocations such as python3 python/ship.py ... or python3 python/report_tokens_cli.py ... stop running the command even though keeping them would not add shims or selectors
- **Proposed resolution**: Keep the __main__ blocks as compatibility pass-throughs while updating all shipped consumers and docs to the cli.py direct-call convention; enforce the new convention with stale-reference lint/docs rather than disabling the old module entrypoints



