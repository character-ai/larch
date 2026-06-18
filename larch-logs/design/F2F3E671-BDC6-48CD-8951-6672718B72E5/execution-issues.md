### External Reviewer Issues

- **Step design Step 3 — collect-results cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-requirements-output.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/cursor-plan-requirements-output.txt)

Reviewing the plan against the issue scope and validating cited integration points in the codebase.
schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	completeness	scripts/parse-drafter-output.py:1-12	Plan commits to in-process sentinel parsing in python/agents.py but keeps parse-drafter-output.py deletion conditional	If implementer treats the conditional delete as optional, scripts/parse-drafter-output.py and harness siblings can remain while python/checks.py _DIRECT_TARGET_RULES still route edits there, breaking make lint-retired-scripts and leaving a shim-adjacent duplicate parser	Make deletion mandatory: after porting parser logic into python/agents.py, always delete scripts/parse-drafter-output.py plus .md and test-parse-drafter-output.* siblings and append them to python/migrated-scripts.tsv
2	in_scope	important	correctness	python/checks.py:1629-1649	Plan allows lint-fix stderr-tail replacement from python/agents.py or review_dispatch	review_dispatch.render_failed_agent_stderr_tail only renders text; it does not write ${output}.stderr-tail sidecars like bash write_failed_agent_stderr_tail, so choosing review_dispatch would drop failure sidecars lint-fix relies on today	Specify checks.py must call the agents.py sidecar writer (_write_stderr_tail or exported equivalent) and reserve review_dispatch for collector render paths only
3	in_scope	important	correctness	scripts/launch-claude-drafter.sh:324-330	Plan lists generic failure handling but omits the Claude drafter-specific write_failure_diag gate	Codex drafter failures often use short marker files; Claude failures call write_failed_agent_stderr_tail then write_failure_diag only when ${OUTPUT}.failure-diag is empty. Missing this branch loses composed carrier diagnostics on Claude drafter fallback classification	Add an explicit launch_claude_drafter failure step: on non-zero exit, write stderr-tail from ${OUTPUT}.stderr when present, then call the ported write_failure_diag/_compose_failure_diag with --sink only when the carrier is still empty
4	in_scope	important	risk-integration	python/agents.py:1299-1303	Plan fixes _tail_redacted byte-cap semantics but leaves dual stderr-tail authorities across agents and review_dispatch	agents._tail_redacted uses character slicing while review_dispatch.render_failed_agent_stderr_tail already UTF-8 byte-truncates via _truncate_utf8; dual paths risk inconsistent 5120-byte caps between lint-fix, drafter, and collector surfaces	Consolidate on one shared stderr-tail renderer (export from agents or have agents delegate to review_dispatch._truncate_utf8) and point checks.py, collect_results.py, and drafter code at that single helper

**1. completeness / `scripts/parse-drafter-output.py`** — Full in-process port is specified, but deletion stays conditional. That can leave the standalone parser and stale `python/checks.py` routing. Commit to always deleting it after the port lands.

**2. correctness / `python/checks.py:1629-1649`** — The plan’s “agents.py or review_dispatch” choice is unsafe. `review_dispatch.render_failed_agent_stderr_tail` renders only; it does not write `.stderr-tail` sidecars. Lint-fix must use the agents sidecar writer.

**3. correctness / `scripts/launch-claude-drafter.sh:324-330`** — Claude drafter failures use a two-step path: stderr-tail write, then `write_failure_diag` only when the carrier is still empty. The plan should spell that out so Claude drafter failures keep the same diagnostics as today.

**4. risk-integration / `python/agents.py:1299-1303`** — Two stderr-tail implementations (`_tail_redacted` vs `review_dispatch._truncate_utf8`) invite cap drift. Pick one shared UTF-8 byte-cap helper for lint-fix, drafter, and collector paths.
## Reviewer stderr (<TMPDIR>/cursor-plan-requirements-output.txt.diag)

(empty: <TMPDIR>/cursor-plan-requirements-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/cursor-plan-requirements-output.txt.stderr-tail)

(file missing: <TMPDIR>/cursor-plan-requirements-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/cursor-plan-requirements-output.txt.launch-stderr)

⏳ cursor agent: still running (1m elapsed)
⏳ cursor agent: still running (2m elapsed)
⏳ cursor agent: still running (3m elapsed)
⏳ cursor agent: still running (4m elapsed)
⏳ cursor agent: still running (5m elapsed)
⏳ cursor agent: still running (6m elapsed)
✓ cursor agent: completed (exit code 0, output 4151 bytes)
  ```
