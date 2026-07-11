## Proposed Design Outline

### Goals
- Preserve publish-failure diagnostics: keep bounded stdout/stderr tails and the exception traceback so they flush and reach the auto-issue.
- Report salvageable exit-5 runs correctly: class recoverable with a resume hint when the plan already wrote.
- Keep accurate on-disk state after a crash so post-mortems and the reporter agree.

### Non-goals
- Do not change the publish logic, retry counts, or the rc-4 fail-closed assessment gate.
- Do not change /implement retry_policy caps or auto-retry behavior.
- Do not alter the run-log flush PR machinery.

### Approach sketch
- In design_step5c.py, copy bounded publish stdout/stderr tails into DESIGN_TMPDIR before unlinking the temp captures; feed the stderr tail into design-publish-tail.failure.log; emit PUBLISH_RC_SOURCE=exception|returned plus the first traceback line.
- In design_publish.py publish_core, add phase-progress markers (post-plan-write, post-rename, log-publish leg), rewrite the result env on every rc-5 path, and surface _write_result_env failures.
- In _classify.py add a publish/rc-5/publish-tail-failed pattern; thread plan-write success into the terminal state so the reporter reports recoverable with a rename+log-flush resume hint and populates branch/PR/issue.
- Amend or close the auto-filed issue when a salvage later succeeds in the same session.

### Surfaces in scope
- python/larch/design/design_step5c.py
- python/larch/design/design_publish.py
- python/larch/design/design_terminal.py
- python/larch/state/_classify.py (and _detail_log.py, _report.py failure-detail wiring)
- result-env and terminal-state key allowlists

### Open questions
- Salvage-success detection hook: central tail-publish success and/or a later approved outcome for the same issue (resolved in plan drafting).
