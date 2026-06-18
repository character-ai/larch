### External Reviewer Issues

- **Step design Step 3 — collect-results cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-requirements-output.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/cursor-plan-requirements-output.txt)

Reading the plan and checking cited paths against the issue scope.
schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	completeness	skills/implement/scripts/test-step-8-ship.sh:7-42	Retired-path deletion omits the Step 8 ship offline harness that `make lint` still runs via `test-harnesses-5`	`test-step-8-ship.sh` statically reads `step-8-ship.sh`, `step-8-seed-initial.sh`, and `step-8-python-guard.sh` and asserts they source `lib-implement-clone-tag.sh`. Deleting those wrappers without retargeting or replacing this harness breaks `make test-step-8-ship` / `make lint`	Add `### UPDATED: skills/implement/scripts/test-step-8-ship.sh` (retarget to `implement step8-ship` / `implement step8-seed-initial` / `implement step8-python-guard`) or fold coverage into `python/test_ship.py` and repoint the Makefile `test-step-8-ship` target before deleting the bash wrappers
2	in_scope	important	completeness	skills/implement/scripts/lib-implement-clone-tag.sh:1-14	Clone-tag shell helper is extracted to Python but not listed for retirement or manifest append	After `step-8-ship.sh` and `step-8-seed-initial.sh` are deleted, `lib-implement-clone-tag.sh` / `.md` become orphaned while `test-implement-structure.sh` and `test-step-8-ship.sh` still pin shell sourcing semantics; `make lint-retired-scripts` may also leave stale live references	Append `skills/implement/scripts/lib-implement-clone-tag.sh` and sibling `.md` to the retired-path delete list and `python/migrated-scripts.tsv`; update structure/ship harness needles to assert the shared Python helper instead of shell `source`
3	in_scope	important	risk-integration	python/bootstrap.py:487-488	Resume prelude is documented but the failing sentinel branch is not named as a required fix	`step-0-bootstrap.sh` currently pre-seeds `TARGET_ISSUE_NUMBER` from `parent-issue.md` before `bootstrap invoke`. Calling `bootstrap invoke --mode resume` directly (per Step 0 cutover) with cleared shell exports still hits `issue-number-required-for-resume` when `st.opts.issue_number` is empty even though a valid adopted sentinel exists	In `invoke_main` resume prelude (or `_phase_tracking`), read `parent-issue.md` via `tracking-issue read --sentinel` and bind `issue` / `run_id` before `run_bootstrap`, or change the sentinel branch to adopt issue/run_id when `resume_plan_tail` and sentinel are valid; keep `test_bootstrap.py` dirty-tree resume coverage
4	in_scope	important	completeness	plan.txt:342-363	[SCOPE-REDUCTION] Pre-deletion parity gate omits several `make lint` shell harnesses tied to bodies this issue retires	Retired-path section deletes OOS and execution-issues bash plus `test-flush-execution-issues.sh`, `test-refresh-execution-issues.sh`, `test-post-tracking-issue.sh`, `test-slack-issue-announce.sh`, `test-materialize-manifest-oos.sh`, and `test-oos-*` harnesses, but the testing strategy only lists implement-structure/timing/step8-exit3 harnesses before deletion; pytest ports alone do not prove Makefile `test-harnesses-6/15/18` targets stay green	Extend pre-deletion parity to either (a) run and green the listed shell harnesses against the new CLI surfaces before deletion, or (b) explicitly retarget each Makefile `test-*` target to pytest in the same PR tranche and list those targets under `### UPDATED: Makefile`
5	out_of_scope	latent	architecture	scripts/test-references-headers.sh:52	Contract-header sweep for deleted OOS helper docs is not listed	`scripts/test-references-headers.sh` still expects `skills/implement/scripts/materialize-manifest-oos.md`; deleting the helper `.md` without updating this script may fail `make lint` later	Add `scripts/test-references-headers.sh` to the doc/harness sweep or drop the materialize-manifest row when the sibling contract is retired
6	out_of_scope	nit	code-quality	skills/implement/scripts/step-0-bootstrap.sh:251-253	Non-resume progress breadcrumb migration is unspecified	Direct `bootstrap invoke` cutover drops the wrapper-only `progress: type p (or progress) at any time` line on initial Step 0 unless replicated elsewhere	If operator UX matters, emit the same line from `invoke_main` on `--mode initial` success; otherwise document intentional removal
## Reviewer stderr (<TMPDIR>/cursor-plan-requirements-output.txt.diag)

(empty: <TMPDIR>/cursor-plan-requirements-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/cursor-plan-requirements-output.txt.stderr-tail)

(file missing: <TMPDIR>/cursor-plan-requirements-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/cursor-plan-requirements-output.txt.launch-stderr)

⏳ cursor agent: still running (1m elapsed)
⏳ cursor agent: still running (2m elapsed)
✓ cursor agent: completed (exit code 0, output 4608 bytes)
  ```
