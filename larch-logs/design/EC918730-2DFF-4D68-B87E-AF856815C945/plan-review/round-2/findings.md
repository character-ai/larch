### FINDING_1:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: nit
- **Focus area**: architecture
- **Location**: scripts/larch-log.sh:67-97
- **Concern**: The proposed dynamic Codex allow arm duplicates the existing broad `*-output*.txt` allow and adds no behavior after the plan confirms there is no exclusion bug.. Scenario: The allowlist becomes harder to reason about for a contract-only clarification, increasing pattern-order surface without fixing runtime behavior.
- **Proposed resolution**: Skip the new case arm; add the explanatory comment next to the existing broad allow and keep the regression tests/docs that pin dynamic Codex inclusion.

### FINDING_2:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: nit
- **Focus area**: architecture
- **Location**: scripts/larch-log.sh:67-96
- **Concern**: Proposed explicit dyn-Codex allow case branch is redundant with the existing broad *-output.txt / *-output-*.txt allow at line 95; verification finding already states behavior is unchanged. Scenario: Issue acceptance needs contract clarity and regression fixtures, not another ordering-sensitive case arm; new write-round assertions still pass if the branch is omitted, while mis-ordering the new arm before prompt denies reintroduces leak risk the plan itself calls out
- **Proposed resolution**: For SIMPLE minimum change, skip the runtime allow clause; document dyn-Codex retention beside the existing broad allow in scripts/larch-log.md and keep phased/cap-hit/prompt fixtures in scripts/test-larch-log-write-round.sh

### FINDING_3:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: security
- **Location**: scripts/larch-log.sh:70, scripts/test-larch-log-write-round.sh:103-147
- **Concern**: The plan says dynamic Codex `.events.jsonl` must remain denied, but the proposed regression tests only add prompt-sidecar negatives.. Scenario: An implementation could accidentally allow dynamic Codex `.events.jsonl` as a JSON-like sidecar while passing the planned tests, committing raw telemetry that may contain prompts, responses, repo snippets, or tool output.
- **Proposed resolution**: Add one dynamic Codex `.events.jsonl` fixture and `assert_not_file` check in `scripts/test-larch-log-write-round.sh`, alongside the planned prompt-sidecar negative.

### FINDING_4:
- **Reviewer(s)**: Cursor-dyn-doc-sync
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-larch-log-write-round.md:11-25
- **Concern**: Companion harness doc sync is optional in the plan but contract changes add phased dynamic Codex, cap-hit, and prompt-negative coverage. Scenario: Implementers skip doc updates because unphased dynamic Codex is already documented; phased and negative-sidecar rules exist only in the shell harness
- **Proposed resolution**: Add an explicit ### UPDATED: scripts/test-larch-log-write-round.md step listing phased dynamic Codex, cap-hit, and prompt-exclusion bullets (drop the “only if summaries name” gate for this file)

### FINDING_5:
- **Reviewer(s)**: Codex-dyn-doc-sync
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: <TMPDIR>/plan.txt:49-51; scripts/test-lib-design-round-artifacts.md:absent
- **Concern**: Plan conditionally names a companion doc that does not exist. Scenario: `find` shows `scripts/test-larch-log-write-round.md` exists, but there is no `scripts/test-lib-design-round-artifacts.md`; following the conditional sync note can add an unnecessary new doc or send the implementer chasing a missing target
- **Proposed resolution**: Revise the note to mention only existing companion docs: keep conditional sync for `scripts/test-larch-log-write-round.md` if its summary changes, and rely on `scripts/test-lib-design-round-artifacts.sh` plus `scripts/lib-design-round-artifacts.md` for the design-round artifact contract
