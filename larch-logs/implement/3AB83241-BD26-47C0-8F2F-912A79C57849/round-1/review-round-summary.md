# Review Round 1

- Mode: `diff`
- 8 accepted, 4 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Prose `Blocks #N` parser over-matches non-dependencies
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `_BLOCKS_RE` can match negated prose, inline code, and examples. This can create false dependency edges from text that does not state a blocker.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_10: `apply_main --defer-close` creates combined issues before validating source numbers
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Malformed `--source-issues` can create a combined host before later dependency or close steps fail. This can orphan a new issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_16: Missing `close-eligible` fail-closed regression coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Tests do not cover failed or missing safe writes, unresolved exceptions, and approved successful exception writes. Closure could regress and close sources too early.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_2: `list_open_main` fails open on GitHub or JSON errors
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `list_open_main` returns exit 0 with `status=failed` and an empty issue list. Downstream planners can proceed with empty metadata and miss required dependencies.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_23: Deferred closure can close sources that became busy
- **Reviewer(s)**: dyn-risk-integration-output.txt
- **Severity**: important
- **Concern**: Sources remain open during the deferred window. If a source gains a busy prefix before closure, `close_sources_main` can still close it and orphan an active workflow.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-risk-integration-output.txt: Address the concern above.


### FINDING_3: `prose_audit_main` drops combined issue endpoints absent from open metadata
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-arch-output.txt
- **Severity**: important
- **Concern**: `prose_audit_main` builds endpoint metadata only from `open-issues-file`. Combined issues missing from that snapshot can have valid fetched prose candidates silently dropped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-arch-output.txt: Address the concern above.


### FINDING_7: OOS audit uses `$REPO` before initialization
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: The OOS audit command passes `--repo "$REPO"`, but the skill does not initialize `REPO`. Empty repo values can make comment dependency reads silently miss data.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_8: `plan_audit_main` trusts malformed Tier-2 candidate `source_kind`
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Tier-2 semantic candidates can be treated as Tier-1 safe auto-writes when `source_kind` is missing or malformed. This can bypass required operator approval.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt: Address the concern above.


