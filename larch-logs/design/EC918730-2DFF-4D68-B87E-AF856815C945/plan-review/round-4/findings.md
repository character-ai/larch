### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/larch-log.sh:67-95
- **Concern**: Proposed explicit dynamic-Codex case arm is not load-bearing because the broad *-output*.txt/*-output-*.txt allow at line 95 already includes the same basenames. Scenario: A typo or incomplete pattern list in the new arm would not fail tests or change committed logs; the explicit clause could document a false contract while behavior still follows the broad arm
- **Proposed resolution**: For minimum change skip the new return-0 arm and add only comment plus test-larch-log-write-round.sh fixtures; if the explicit arm stays add test-larch-log.sh assert_round_artifact_included pins or narrow the broad arm so the new clause is authoritative

### FINDING_2:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lib-design-round-artifacts.sh:5-15; scripts/test-lib-design-round-artifacts.sh:53-55; scripts/lib-design-round-artifacts.md:21-28
- **Concern**: Plan omits the required /design log surface from the feature scope. Scenario: The stated feature decisions include both implement logs and design logs, including fixing the dead codex-plan-*-output.txt exclusion pattern and adding static/dynamic Codex design-log fixtures. If implemented as planned, only scripts/larch-log.sh and its tests/docs change, leaving design Codex exclusions implicit via catch-all behavior and untested.
- **Proposed resolution**: Add minimum UPDATED sections for scripts/lib-design-round-artifacts.sh, scripts/test-lib-design-round-artifacts.sh, and scripts/lib-design-round-artifacts.md: replace or augment the dead codex-plan-*-output.txt raw-output exclusion with actual codex-primary-plan-*-output.txt coverage, add explicit dyn-Codex exclusion fixtures, and include the design artifact test in the testing strategy.

### FINDING_3:
- **Reviewer(s)**: Cursor-dyn-pattern-logic
- **Severity**: nit
- **Focus area**: correctness
- **Location**: plan.txt:12-13
- **Concern**: Plan lists denied sidecar suffixes (.prompt, .diag, .done, .sidecar, .dirty-tree, .untracked-baseline, .events.jsonl) without anchoring them to the existing scripts/larch-log.sh:70 case arms. Scenario: An implementer could add an overly broad dyn-*-codex-output* allow glob or mis-order the new clause without realizing .prompt denial uses *-output.txt.prompt|*-output-*.txt.prompt (not *.prompt) and .events.jsonl uses *.events.jsonl on the same arm
- **Proposed resolution**: In the plan UPDATED scripts/larch-log.sh bullet, map each denied suffix to scripts/larch-log.sh:70 literals and restate insertion is immediately after line 77 and before line 95

### FINDING_4:
- **Reviewer(s)**: Codex-dyn-pattern-logic
- **Severity**: latent
- **Focus area**: security
- **Location**: scripts/larch-log.sh:70-83,scripts/larch-log.sh:95-96
- **Concern**: The proposed “dynamic Codex allow third” insertion point can precede the existing `*-vote-prompt.txt` deny. The phased allow `dyn-*-codex-output-*.txt` would also match a basename like `dyn-api-contract-codex-output-vote-prompt.txt`, so this prompt-shaped deny is not safely anchored by the plan’s ordering.. Scenario: If an output-shaped dynamic Codex vote prompt ever appears in the round source, inserting the allow immediately after the static Codex deny would commit it before the later vote-prompt deny runs.
- **Proposed resolution**: Revise the plan to place the explicit dynamic Codex allow after all deny clauses through `*-vote-prompt.txt` and the zero-byte placeholders, while still before the broad `*-output.txt` allow; or narrow the phased dynamic glob to actual phase/retry forms that cannot overlap prompt names.

### FINDING_5:
- **Reviewer(s)**: Cursor-dyn-doc-narrative-sync
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/larch-log.md:30-33 vs plan.txt:36-44
- **Concern**: The larch-log.md update bullets only say to note an explicit allow clause and unchanged behavior; they do not tell the implementer to extend Dynamic Codex prose for phased forms, while test-larch-log-write-round.md bullets explicitly document phased `dyn-*-codex-output-*.txt` plus `.meta`/`.json`/`.cap-hit` inclusion.. Scenario: After landing, the primary contract doc can still describe only unphased `dyn-*-codex-output.txt` (lines 30-31) while the companion harness doc documents phased inclusion — cross-file narrative drift and a stale allow boundary in `larch-log.md`.
- **Proposed resolution**: Add matching larch-log.md bullets: phased dynamic Codex outputs and sidecars are explicitly allowed; unphased `.cap-hit` remains documented; revise lines 30-33 instead of appending a standalone paragraph.

### FINDING_6:
- **Reviewer(s)**: Cursor-dyn-doc-narrative-sync
- **Severity**: nit
- **Focus area**: architecture
- **Location**: plan.txt:36-40 vs plan.txt:42-48
- **Concern**: The test-larch-log-write-round.md update list covers new fixtures only; it never states that the new explicit clause is contract documentation with unchanged runtime behavior, unlike the Approach section and the larch-log.md update instruction.. Scenario: A reader of only the harness contract may treat phased/cap-hit/prompt assertions as new runtime policy rather than regression coverage for an already-broad allow.
- **Proposed resolution**: Add one test-md bullet: new assertions document an explicit allow clause in `round_artifact_included()`; inclusion behavior is unchanged.

### FINDING_7:
- **Reviewer(s)**: Codex-dyn-doc-narrative-sync
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/larch-log.md:26-46; <TMPDIR>/plan.txt:36-44
- **Concern**: The plan updates test-larch-log-write-round.md to document phased dynamic Codex inclusion, but the larch-log.md instructions only say to clarify the explicit allow clause and do not update the existing write-round allow/deny enumeration, which currently names only unphased dynamic Codex sidecars.. Scenario: After implementation, scripts/test-larch-log-write-round.md and the shell tests would say phased dyn-*-codex-output-*.txt .meta .json .cap-hit are included, while scripts/larch-log.md could still imply only unphased dyn-*-codex-output.txt sidecars are part of the contract.
- **Proposed resolution**: Extend the scripts/larch-log.md step to update the existing write-round enumeration so it explicitly covers both unphased and phased dynamic Codex .txt .meta .json and .cap-hit inclusion, while preserving the unchanged-behavior framing and existing prompt/events exclusions.

### OOS_1:
- **Description**: Phased static Codex fallback fixtures (`codex-specialist-security-output-phase2.txt` and `.meta`, included) are added to the harness, but neither doc-update section says to document phased static Codex inclusion in `scripts/test-larch-log-write-round.md` (larch-log.md already covers this at lines 28-29).. Scenario: The harness doc will assert phased static Codex inclusion without describing it; same pre-existing gap as phased Cursor (already tested at test-larch-log-write-round.sh:125).
- **Reviewer**: Cursor-dyn-doc-narrative-sync
- **Severity**: latent
- **Focus area**: correctness
- **Location**: plan.txt:31-34 vs plan.txt:36-40
- **Phase**: design
