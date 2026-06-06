## Proposed Design Outline

### Goals
- Close three recoverable DX/doc-hardening gaps the #3448 soak run hit in the `/implement` orchestrator (issue items 1, 3, 4).
- Make each fix the cheapest effective change, with no behavior change to the ship path.

### Non-goals
- Item 2 (Python ship `Invoke:` fence): already resolved at repo HEAD — no work.
- No `--help` overhaul (#2679), no `python/ship.py` `--state-file` contract pin.
- No strict-mode or shebang change to the sourced `lib-implement-round-cap.sh`; `count_prior_degraded_rounds` sourcing stays byte-unchanged.

### Approach sketch
- Item 1: `implement-bootstrap-invoke.sh` self-derives `CLAUDE_PLUGIN_ROOT` from `$0` when unset, keeping the loud `:?` guard so broken layouts still abort.
- Item 3: `append-execution-issue.sh` `fail_usage` adds a labeled `USAGE=` synopsis line while keeping the existing `ERROR=usage:` line.
- Item 4: `lib-implement-round-cap.sh` gains a direct-exec `--count-prior-degraded` CLI behind a `BASH_SOURCE` guard; SKILL.md Step 5 banner calls it instead of re-authoring glob/loop bash.

### Surfaces in scope
- `scripts/implement-bootstrap-invoke.sh` (+ sibling `.md`, existing test)
- `scripts/append-execution-issue.sh` (+ sibling `.md`, new test + Makefile target)
- `scripts/lib-implement-round-cap.sh` (+ sibling `.md`, existing test)
- `skills/implement/SKILL.md` — "### Scripted review loop" banner paragraph only

### Open questions
- None.
