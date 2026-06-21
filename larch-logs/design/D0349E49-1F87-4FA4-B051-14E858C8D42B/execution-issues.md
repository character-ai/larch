### External Reviewer Issues

- **Step design Step 3 — collect-results cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-1/cursor-plan-innovation-output.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-1/cursor-plan-innovation-output.txt)

Reviewing the plan and tracing the cited Bash libraries and Python integration points in the codebase.
schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	completeness	skills/design/scripts/test-trailer-helpers.sh:1-45	Orphan combined trailer harness survives child deletions	Plan deletes test-trailer-awk.sh, test-trailer-dedup.sh, test-trailer-has-any.sh, and test-trailer-validate.sh plus lib-plan-optional-trailers.sh but not test-trailer-helpers.sh. The script still sources the deleted lib and invokes deleted adapters; it also stays listed in scripts/residual-bash-paths.txt:106 while sibling rows are removed. make test-trailer-helpers already runs pytest only, so CI stays green while the tracked shell harness becomes a broken dead entry.	Add DELETE steps for skills/design/scripts/test-trailer-helpers.sh, remove its residual-bash-paths.txt row, and append it to python/migrated-scripts.tsv with the other retired trailer harnesses.
2	in_scope	important	risk-integration	agent-lint.toml:1062-1065	Stale G004 exclusions for deleted clone-tag bash lib	agent-lint.toml excludes skills/implement/scripts/lib-implement-clone-tag.sh and .md because G004 does not follow shell source edges. After deletion, step-8-seed-initial.sh and step-8-ship.sh will call python/cli.py implement clone-tag directly with no replacement pin. make lint agent-lint can flag the new verb as unreachable from SKILL.md or treat deleted exclude paths as stale wiring.	Remove the lib-implement-clone-tag exclude rows and add a structured G004 pin for python/cli.py implement clone-tag from the Step 8 wrappers (mirror other implement CLI pins in agent-lint.toml / skills/implement/SKILL.md Extracted Script Registry).
3	in_scope	important	correctness	skills/implement/scripts/step-8-seed-initial.sh:15-16	Plan omits seeder wrapper from explicit clone-tag eval list	Only step-8-ship.sh is named for the eval "$(python3 ... implement clone-tag)" swap; step-8-seed-initial.sh still sources lib-implement-clone-tag.sh today and must emit the same EXPECTED_TMPDIR_BASENAME_PREFIX as ship. Updating ship alone revives seed vs ship prefix drift and Step 18 cleanup mismatch called out in the plan failure modes.	Explicitly list skills/implement/scripts/step-8-seed-initial.sh in the clone-tag repoint section with the same eval line as step-8-ship.sh (the file is in Files to modify/create but the Approach bullets only mention step-8-seed-initial.sh in passing).


- **findings aggregator**: merged output failed validation; leaving <TMPDIR>/findings-in-scope.md unchanged. See <TMPDIR>/aggregator-validate.stderr.

- **Step design Step 3 — collect-results cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-2/cursor-plan-requirements-output.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-2/cursor-plan-requirements-output.txt)

Reviewing the plan against the issue scope and verifying cited files in the codebase.
schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	completeness	skills/implement/scripts/step-8-ship.md:3,18	step-8-ship.md still documents sourcing lib-implement-clone-tag.sh but the plan leaves that file unchanged	The plan deletes lib-implement-clone-tag.sh and appends it to python/migrated-scripts.tsv while the UPDATED step-8-ship.md section only says keep the driver contract unchanged. Lines 3 and 18 will still cite the retired helper, so make lint-retired-scripts fails after manifest append (the plan failure-modes section already warns about missing docs cleanup)	In the step-8-ship.md UPDATED section, replace lib-implement-clone-tag.sh sourcing prose with fail-closed python/cli.py implement clone-tag capture/eval, matching step-8-seed-initial.md
2	in_scope	important	completeness	python/migrated-scripts.tsv:215-221	migrated-scripts.tsv append example omits several paths the plan deletes elsewhere	The subsection lists only lib-plan-optional-trailers.* and test-trailer-awk.md even though the plan also deletes lib-implement-clone-tag.sh/.md and five test-trailer-*.sh harnesses. A manifest append that follows only the short example leaves those retirements unrecorded, breaking the acceptance criterion to record every deletion in the manifest and risking missed reference cleanup	Expand the migrated-scripts.tsv bullet to enumerate every deleted path from the Files section (both libs, all test-trailer-*.sh, test-trailer-awk.md, lib-implement-clone-tag.sh/.md) with #4971, or add an explicit cross-check step before make lint-retired-scripts
## Reviewer stderr (<TMPDIR>/plan-review/round-2/cursor-plan-requirements-output.txt.diag)

(empty: <TMPDIR>/plan-review/round-2/cursor-plan-requirements-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-2/cursor-plan-requirements-output.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-2/cursor-plan-requirements-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-2/cursor-plan-requirements-output.txt.launch-stderr)

⏳ cursor agent: still running (1m elapsed)
⏳ cursor agent: still running (2m elapsed)
⏳ cursor agent: still running (3m elapsed)
⏳ cursor agent: still running (4m elapsed)
✓ cursor agent: completed (exit code 0, output 2046 bytes)
  ```

- **Step design Step 3 — collect-results cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/plan-review/round-4/cursor-plan-requirements-output.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/plan-review/round-4/cursor-plan-requirements-output.txt)

Reviewing the plan against the feature scope and tracing cited files in the codebase.
schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	completeness	python/test_residual_bash.py:36-46	Orchestration fixture repair omits manifest-listed lib-implement-clone-tag.sh	The plan drops only lib-plan-optional-trailers.sh from test_manifest_excludes_non_residual_orchestration while also manifest-deleting lib-implement-clone-tag.sh. The unsplit literal skills/implement/scripts/lib-implement-clone-tag.sh remains at line 42 and will trip make lint-retired-scripts after manifest append, failing the acceptance criterion even when wrappers and docs are updated.	Also drop or split the lib-implement-clone-tag.sh orchestration entry (for example skills/implement/scripts/ + lib-implement-clone-tag.sh) in the same mandatory test_residual_bash.py repair step; mirror the explicit drop already listed for lib-plan-optional-trailers.sh.
2	in_scope	important	correctness	python/implement_dispatch.py:27-35	Clone-tag sanitization spec says bytes but proposes str-level re.sub	The plan requires per-byte tr -c parity and 32-byte truncation on the sanitized byte string, but the implementation sketch equates that to re.sub on a Unicode basename string. For non-ASCII UTF-8 basenames, str-level replacement can emit one underscore per code point while bash tr -c emits one per byte, changing CLONE_TAG_FULL and breaking the stated byte-for-byte retirement contract.	Implement _derive_clone_tag_full via os.fsencode(os.path.basename(os.environ["PWD"])) (or equivalent bytes pipeline), sanitize and truncate on bytes, then decode for prefix assembly; keep the planned PWD-vs-cwd and regression tests.
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
✓ cursor agent: completed (exit code 0, output 2083 bytes)
  ```
### 1. Orphan `test-trailer-helpers.sh`
The retirement-only trailer path is sound: runtime already uses `python/cli.py plan optional-trailers` and `plan_review.py` gate-b-dedup. Deleting the awk/sh stack without deleting the combined harness leaves a inconsistent residual inventory.

### 2. `agent-lint.toml` clone-tag pins
Minimum-change migration should swap source-based exclusions for CLI reachability pins, not only delete the bash lib.

### 3. Seeder wrapper parity
`step-8-seed-initial.sh` is in the file list but easy to miss during implementation because Approach prose emphasizes `step-8-ship.sh` first.

[OUT_OF_SCOPE] **architecture** `python/session_env.py:1507-1510` — A third cwd-only clone-tag sanitizer exists without `CLONE_TAG` override. Unifying it with the new helper would reduce long-term drift on multi-clone hosts, but that predates this PR and is not required to delete the sourced bash libs.

[OUT_OF_SCOPE] **architecture** `python/implement_dispatch.py` — Placing `implement clone-tag` in `implement_dispatch.py` is acceptable; a dedicated `session_env` export helper would be cleaner but adds surface beyond the issue’s “cli.py verb + repoint consumers” ask.
## Reviewer stderr (<TMPDIR>/plan-review/round-1/cursor-plan-innovation-output.txt.diag)

(empty: <TMPDIR>/plan-review/round-1/cursor-plan-innovation-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/plan-review/round-1/cursor-plan-innovation-output.txt.stderr-tail)

(file missing: <TMPDIR>/plan-review/round-1/cursor-plan-innovation-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/plan-review/round-1/cursor-plan-innovation-output.txt.launch-stderr)

⏳ cursor agent: still running (1m elapsed)
⏳ cursor agent: still running (2m elapsed)
⏳ cursor agent: still running (3m elapsed)
⏳ cursor agent: still running (4m elapsed)
✓ cursor agent: completed (exit code 0, output 4060 bytes)
  ```
