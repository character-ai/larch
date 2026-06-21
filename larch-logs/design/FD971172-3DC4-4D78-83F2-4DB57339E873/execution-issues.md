### External Reviewer Issues

- **Step design Step 3 — collect-results cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-1/cursor-plan-innovation-output.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-1/cursor-plan-innovation-output.txt)

Reading the plan and tracing cited code paths to validate the proposed migration.
schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	risk-integration	python/oos_filer.py:788-794	[SCOPE-REDUCTION] Plan ports Bash parity into `file_conflict_deps` / `file_conflict_deps_main` but omits the active `/implement` Step 9a.1 caller that bypasses the CLI.	`python/cli.py oos file` calls `file_oos.file_conflict_deps()` in-process and always passes `deps_path` to `_run_issue_batch`. It only catches `OSError`, never deletes a stale `oos-intra-batch-deps.tsv` on failure, and never applies global-cap exit-1 degrade semantics from `oos-pipeline.md` step 3.5. A cap failure can abort the whole `oos file` run or leave prior-run TSV rows applied. Add `### MAY_UPDATE: python/oos_filer.py`: invoke `python/cli.py oos file-conflict-deps` like `python/design_oos.py:305-320` and `skills/implement/references/oos-pipeline.md` step 3.5 (mirror `deps_available` + `unlink` on failure; pass `deps_path=None` when degraded). If the in-process call stays, extend the same failure contract and add `python/test_oos_filer.py` coverage for cap failure and stale-file cleanup.
1	in_scope	important	correctness	python/file_oos.py:773-781	Batch indices must be parse ordinals, not `### OOS_N:` heading numbers.	The migrated Bash harness case-t expects `1\t4` while the last heading is `### OOS_3:`; today's `_parse_oos_blocks` uses heading digits (`int(match.group(1))`). Using heading numbers breaks malformed-slot preservation and generic/pending-heading cases. In `### UPDATED: python/file_oos.py`, state explicitly: index `i` is `enumerate(parse_issue_input(...)[0], start=1)`; never read `N` from `OOS_N` headings; malformed items keep their slot but contribute zero path records.
1	in_scope	important	correctness	skills/implement/scripts/oos-file-conflict-deps.sh:276-291	Plan does not pin the one-edge-per-pair candidate rule.	Bash emits at most one candidate edge per unordered item pair (first conflicting shared path, then `break`). Wording like "edges for shared paths" can yield multiple rows per pair, changing union-find components, cluster-cap chain degradation, and global-cap counts versus fixtures case-e and case-j. Add an explicit plan bullet: for each pair `(i,j)`, scan shared paths in stable order; on first conflict emit one `(i,j)` row, union, and stop scanning that pair.
1	in_scope	latent	correctness	skills/implement/scripts/oos-file-conflict-deps.sh:115-119	Plan omits `clean_match` boundary trimming after regex extraction.	Bash strips leading non-alphanumeric/non-dot prefixes and trailing non-path punctuation before path-safety checks (`clean_match`). Skipping this step can drop or mis-parse mentions that the voting regex captures with adjacent punctuation, diverging from Bash on edge-case bodies beyond the comma/semicolon split. Port `clean_match` literally or document byte-identical trimming in the extraction step.
1	out_of_scope	latent	architecture	skills/implement/references/execution-issues-tracking.md:51	Stale contract pointer after deleting `oos-file-conflict-deps.md`.	The tracking doc still cites `${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/oos-file-conflict-deps.md` as the helper contract; that file is deleted in-plan with no doc repoint to `python/file_oos.py` / pytest fixtures. Follow-up issue: repoint the contract link to the Python verb and migrated tests (no runtime change required for this migration).
## Reviewer stderr (<TMPDIR>/plan-review/round-1/cursor-plan-innovation-output.txt.diag)

(empty: <TMPDIR>/plan-review/round-1/cursor-plan-innovation-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-1/cursor-plan-innovation-output.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-1/cursor-plan-innovation-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-1/cursor-plan-innovation-output.txt.launch-stderr)

⏳ cursor agent: still running (1m elapsed)
⏳ cursor agent: still running (2m elapsed)
✓ cursor agent: completed (exit code 0, output 3862 bytes)
  ```

- **findings aggregator**: merged output failed validation; leaving <TMPDIR>/findings-in-scope.md unchanged. See <TMPDIR>/aggregator-validate.stderr.

- **Step design Step 3 — collect-results cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-4/cursor-plan-requirements-output.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-4/cursor-plan-requirements-output.txt)

Reviewing the plan against the feature scope and verifying cited files and contracts in the codebase.
schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	completeness	python/migrated-scripts.tsv:189-194	Retired harness paths omitted from manifest rows while plan deletes test-oos-file-conflict-deps.sh/.md	The plan deletes the Bash harness and contract doc (lines 205-212) and its own Failure modes section warns that omitting harness rows from migrated-scripts.tsv leaves stale references unenforced, yet the manifest section only lists oos-file-conflict-deps.sh/.md. A missed reference to the deleted harness will not be caught by make lint-retired-scripts.	Add skills/implement/scripts/test-oos-file-conflict-deps.sh and skills/implement/scripts/test-oos-file-conflict-deps.md to the #4967 migrated-scripts.tsv rows (same pattern as skills/shared/scripts/test-oos-serialize.sh/.md).
2	in_scope	important	risk-integration	Makefile:584-585	Migrated pytest cases must stay selected by make test-oos-file-conflict-deps	The Makefile target filters with -k file_conflict_deps. The plan migrates many new cases (lines 95-124) but does not require each migrated test name to include that substring. New cases named only test_case_a_same_file or similar would be skipped by the acceptance command make test-oos-file-conflict-deps while py-test could still pass.	State in python/test_file_oos.py that every migrated harness test name must contain file_conflict_deps (or use a shared prefix like test_file_conflict_deps_case_a) so the existing Makefile -k filter exercises the full migrated fixture set.

## Findings


- **Step design Step 3 — collect-results cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-5/cursor-plan-requirements-output.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-5/cursor-plan-requirements-output.txt)

Reviewing the plan against the feature scope and inspecting cited codebase paths.
schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	completeness	python/migrated-scripts.tsv:190-195	migrated-scripts.tsv add-list names only helper .sh/.md rows though Approach and failure modes require all four retired paths	The ### UPDATED: python/migrated-scripts.tsv bullets list only oos-file-conflict-deps.sh and .md; harness test-oos-file-conflict-deps.sh and .md are deleted elsewhere but omitted from the explicit add-row list, so an implementer can register two paths, delete four files, and still fail make lint-retired-scripts on lingering harness literals in Makefile agent-lint.toml docs/linting.md and scripts/residual-bash-paths.txt	Add skills/implement/scripts/test-oos-file-conflict-deps.sh and skills/implement/scripts/test-oos-file-conflict-deps.md as explicit migrated-scripts.tsv bullets alongside the helper rows (keyed #4967) before deletion
## Reviewer stderr (<TMPDIR>/plan-review/round-5/cursor-plan-requirements-output.txt.diag)

(empty: <TMPDIR>/plan-review/round-5/cursor-plan-requirements-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-5/cursor-plan-requirements-output.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-5/cursor-plan-requirements-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-5/cursor-plan-requirements-output.txt.launch-stderr)

⏳ cursor agent: still running (1m elapsed)
⏳ cursor agent: still running (2m elapsed)
⏳ cursor agent: still running (3m elapsed)
⏳ cursor agent: still running (4m elapsed)
✓ cursor agent: completed (exit code 0, output 1339 bytes)
  ```
### 1. [completeness] `python/migrated-scripts.tsv:189-194` — harness manifest rows missing

The plan deletes `test-oos-file-conflict-deps.sh` and `.md` but only registers the helper script in `migrated-scripts.tsv`. The plan’s own failure-mode note (lines 243-244) says harness rows are needed for mechanical enforcement after deletion. Without them, a leftover reference to the deleted harness will not fail `make lint-retired-scripts`, which is an explicit acceptance criterion.

**Suggested revision:** Add both harness paths to the `#4967` manifest rows, matching the `test-oos-serialize` migration pattern.

### 2. [risk-integration] `Makefile:584-585` — pytest name filter contract unstated

Acceptance requires `make test-oos-file-conflict-deps`, which runs `pytest -k 'file_conflict_deps'`. The plan lists many migrated cases but does not require test names to match that filter. Partial migration could leave the Make target green while most Bash fixtures are not exercised.

**Suggested revision:** Require a `file_conflict_deps` naming convention for all migrated tests in `python/test_file_oos.py`.
## Reviewer stderr (<TMPDIR>/plan-review/round-4/cursor-plan-requirements-output.txt.diag)

(empty: <TMPDIR>/plan-review/round-4/cursor-plan-requirements-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-4/cursor-plan-requirements-output.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-4/cursor-plan-requirements-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-4/cursor-plan-requirements-output.txt.launch-stderr)

⏳ cursor agent: still running (1m elapsed)
⏳ cursor agent: still running (2m elapsed)
⏳ cursor agent: still running (3m elapsed)
⏳ cursor agent: still running (4m elapsed)
⏳ cursor agent: still running (5m elapsed)
⏳ cursor agent: still running (6m elapsed)
✓ cursor agent: completed (exit code 0, output 3140 bytes)
  ```
