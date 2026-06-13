# Review Round 4

- Mode: `diff`
- 5 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Untrusted bootstrap-routing.env skips absorbed continue tail without routing signal
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-architecture-output.txt
- **Severity**: important
- **Concern**: When `bootstrap-routing.env` exists but is not a regular file (e.g. symlink), `invoke_main` skips the absorbed continue tail (degraded gate and `1.r`) without emitting `ROUTE`, `DEGRADED_PROMPT_REQUIRED`, or any explicit skip flag. Resume can exit 0 with continue-shaped stdout but no matching routing-table row; the orchestrator falls through to missing-`ROUTE`/rebase-failure handling instead of a qualified continue, bail, or repair path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Always run the absorbed tail when the continue predicate holds (only refuse to read untrusted cache for restoration), or emit an explicit skip/bail KV plus a SKILL.md routing row.
  - From cursor-specialist-edge-cases-output.txt: Run absorbed tail whenever the fresh envelope satisfies the continue predicate; restrict only coder restore and routing-file writes when the routing file is untrusted.
  - From dyn-architecture-output.txt: Emit an explicit envelope key (for example `ABSORBED_TAIL_SKIPPED=true` with reason `untrusted-routing-file`) and add a matching routing-table row that stalls or forces operator repair before Step 2.


### FINDING_10: Stale harness needles for rebase-checkpoint-routing contract headings
- **Reviewer(s)**: cursor-specialist-testing-output.txt, codex-generic-output.txt
- **Severity**: important
- **Concern**: `scripts/test-implement-rebase-macro.sh` still pins the removed `**Orchestrator contract — parse the wrapper stdout**` heading from `rebase-checkpoint-routing.md`. `scripts/test-implement-structure.sh` has the same stale assertion. CI shards `test-harnesses-3`/`9` fail even when updated docs are correct.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Replace stale needle with the new absorbed-1.r and direct-probe orchestrator contract headings
  - From codex-generic-output.txt: Replace the stale needle with current required anchors, for example `**Orchestrator contract — absorbed \`1.r\`` and `**Orchestrator contract — direct probe fences`.


### FINDING_11: No test for degraded-tools-gate subprocess failure contract path
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Gate CLI non-zero exit should yield `invoke_main` exit 2 with `STEP_FAILED=absorbed-degraded-gate`; this regression path is untested and could let Step 0 proceed or fail opaquely.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add invoke_main-level test stubbing gate CLI non-zero returncode and asserting exit 2 plus step_failed token


### FINDING_16: _resolve_non_interactive does not implement canonical non-interactive predicate
- **Reviewer(s)**: dyn-architecture-output.txt
- **Severity**: important
- **Concern**: `_resolve_non_interactive()` checks env vars (`LARCH_AUTONOMOUS_LOOP`, etc.) and a partial `ps` walk but does not implement the canonical predicate in `skills/shared/external-reviewers.md`. Nothing in-repo sets `LARCH_AUTONOMOUS_LOOP`, and there is no detection of `<<autonomous-loop>>` runs. Misclassification can bounce autonomous runs into an interactive degraded prompt.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-architecture-output.txt: Centralize the canonical predicate in one helper (used by `step-0-bootstrap.sh` and `bootstrap invoke`), and wire the same signals `/implement` already uses for other `AskUserQuestion` carve-outs, including whatever env or argv surface marks autonomous-loop runs.


### FINDING_6: Degraded-gate subprocess failure lacks redacted diagnostic relay
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: When `agent degraded-tools-gate` exits non-zero, the operator sees only a generic absorbed-degraded-gate message with no stderr detail relayed into the bootstrap contract failure path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Pass redacted gate.stderr (and stdout if needed) into _invoke_error before returning bootstrap contract failure exit 2.


