# Extracted script registry

**Consumer**: `/implement` contributors editing extracted script contracts.

**Contract**: Lazy catalog for wrapper/script docs and high-level Python surfaces delegated from `skills/implement/SKILL.md`. This reference is a reader index, not an agent-lint reachability anchor.

**When to load**: Load only when editing or auditing extracted `/implement` script contracts. Normal `/implement` orchestration does not load this catalog.

Prompt-side orchestration steps delegate to these script contracts:

- `post-tracking-issue.md` (`skills/implement/scripts/post-tracking-issue.sh`)
- `skills/implement/references/step2-dispatch.md`
- `generate-code-flow-diagram.md` (`skills/implement/scripts/generate-code-flow-diagram.sh`)
- `refresh-execution-issues.md` (`skills/implement/scripts/refresh-execution-issues.sh`)
- `write-final-report.md` (`skills/implement/scripts/write-final-report.sh`)
- `skills/implement/scripts/cleanup.md` (`skills/implement/scripts/cleanup.sh`)
- `step-0-bootstrap.md`
- `step-0-degraded-gate.md` (`skills/implement/scripts/step-0-degraded-gate.sh`, legacy offline-harness surface not called on the active Step 0 path)
- `step-2-post-dispatch.md` (`skills/implement/scripts/step-2-post-dispatch.sh`)
- `run-step-checks.md`
- `step-5-review.md`
- `step-5-resume.md` (`python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" implement checks-step5-resume --checks-site step5-review-fixes`; `step-5-resume.sh --record-only` retained for terminal timing)
- `step-6-entry.md` (`python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" review-and-fix check-changes`, via `step-6-entry.sh`)
- `step-8-python-guard.md`
- `step-8-seed-initial.md`
- `step-8-ship.md`
- `step-8-oos-checkpoint.md`
- `python/larch/state/closeout.py` (`python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" implement step-16-17`, `step-16`, and `step-17`)
- `step-18.md` (`skills/implement/scripts/step-18.sh`)
- `python/larch/review/review_and_fix.py` (Step 5 / apply-findings / check-changes / commit-fixes / write-rejected driver)

**PR-body recovery helper:** use `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" pr closes-issue` for `Closes #N` extraction.

**Structured invocation pin**: when a workflow needs the PR-body `Closes #N` extractor, call it with no argv:

```bash
[ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/plugin-root.env" ] && . "$IMPLEMENT_TMPDIR/plugin-root.env"
export IMPLEMENT_TMPDIR
[ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ] && CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
export CLAUDE_PLUGIN_ROOT
python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" pr closes-issue
```

Structured invocation pins for script factoring that is reached through active drivers or wrappers:

```text
"${CLAUDE_PLUGIN_ROOT}/python/cli.py" pr compose-summary --plan-goals-file "$IMPLEMENT_TMPDIR/plan-goals.md"
"${CLAUDE_PLUGIN_ROOT}/python/cli.py" render run-summary --skill implement --outcome "$IMPLEMENT_OUTCOME" ...
"${CLAUDE_PLUGIN_ROOT}/python/cli.py" implement-finalize teardown --state-file "$IMPLEMENT_TMPDIR/finalize-state.sh" --implement-tmpdir "$IMPLEMENT_TMPDIR"
python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" checks repair-loop --tmpdir "$IMPLEMENT_TMPDIR" --site <site> --checks-log "$REDACTED_LOG_FILE"
```
