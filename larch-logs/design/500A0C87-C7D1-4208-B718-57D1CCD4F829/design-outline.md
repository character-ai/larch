## Proposed Design Outline

### Goals
- Port `design-clarify.sh` (451-line Bash phase driver) to `python/clarify.py` as `design_clarify_main`
- Register `("design", "clarify")` in `python/cli.py`; thin-wrap `design-clarify.sh` as delegation glue

### Non-goals
- Porting `design-stage-terminal-state.sh` (called best-effort from fetch failures; not in G6.1 scope)
- Changing the wire format of result env files or SKILL.md caller invocations
- Porting other G6 partitions (failure-report, step5b/5c, step6, final-summary)

### Approach sketch
- Add `design_clarify_main`, `_stage_failed_clarify`, `_append_clarify_failure`, `_load_route_state_repo` helpers to `python/clarify.py`
- Fetch phase: call `clarify_state()` + `clarify_comment_fetch()` directly; write `.design-clarify-request.env` + `.design-clarify-fetch-result.env`
- Publish phase: redact via `redact.redact()`; call named-block write / design log-publish / tracking-issue rename via subprocess; call `clarify_comment_post()` + `clarify_label()` directly; write `.design-clarify-publish-result.env`
- Replace ~420 lines in `design-clarify.sh` with ~25-line thin delegation wrapper
- Add ~150 lines of Python tests in `test_clarify.py`

### Surfaces in scope
- `python/clarify.py`
- `python/test_clarify.py`
- `python/cli.py` (`_REGISTRY` + `_MAIN_AGENT_ONLY`)
- `skills/design/scripts/design-clarify.sh`
- `skills/design/scripts/design-clarify.md`
- `skills/design/scripts/test-design-clarify.sh`
- `skills/design/scripts/test-design-clarify.md`

### Open questions
- None.
