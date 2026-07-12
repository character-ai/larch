### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: architecture
- **Location**: skills/implement/references/step2-dispatch.md:41-82
- **Concern**: Step 2 stdout contract still omits CLI-gate `REASON` on `claude_fallback`. Scenario: The plan adds actionable `REASON` text on clean-tree `STATUS=claude_fallback` and changes gate failures from `codex-runtime-failure` bail semantics, but the authoritative Step 2 contract still says `REASON=<token>` is set only when `STATUS=bailed`. Harnesses and SKILL §2.1 cite this file as normative.
- **Proposed resolution**: Add `### UPDATED: skills/implement/references/step2-dispatch.md` documenting optional sanitized `REASON` on CLI-gate `claude_fallback` (clean tree), the dirty-tree forbidden-authority path, and KV sanitization limits; mirror in `python/tests/implement/test_implement_dispatch.py` and the edit-in-sync list.

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:379-382
- **Concern**: CLI-gate upgrade text is not surfaced in operator-visible Step 2 chat. Scenario: The scope anchor lists “only a Warnings line surfaced” as the durable gap. The plan preserves the generic “Codex selection drifted” chat banner and only appends the upgrade `REASON` under `Warnings` in `execution-issues.md`, so operators can still miss the actionable `npm install` message in chat.
- **Proposed resolution**: In the `coder=codex` + `STATUS=claude_fallback` branch, when `REASON` matches the CLI-upgrade detector, print that message in chat (replace the drift banner or add a second visible line) and keep the Warnings log; do not rely on file-only surfacing. ### 1. Step 2 stdout contract omits CLI-gate `REASON` (`architecture`) Round 1 FINDING_1 remains open. The plan updates `dispatch_step2.py` and tests to emit actionable `REASON` on clean-tree `claude_fallback`, but it does not list `skills/implement/references/step2-dispatch.md`, which still restricts `REASON` to `STATUS=bailed`: REASON=<token> # set ONLY when STATUS=bailed That file is the normative stdout grammar for SKILL §2.1 and `python/tests/implement/test_implement_dispatch.py`. Without a firm plan step, implementers can ship Python behavior that contradicts the contract and downstream parsers. **Suggested revision:** Add `### UPDATED: skills/implement/references/step2-dispatch.md` covering optional sanitized `REASON` on CLI-gate `claude_fallback`, the dirty-tree forbidden-authority branch, and the same KV safety rules already used for bailed reasons. ### 2. Upgrade message still hidden from Step 2 chat (`correctness`) The binding issue calls out Warnings-only surfacing as the failure mode: operators saw vague drift text and never got the server’s upgrade instruction. The plan’s `skills/implement/SKILL.md` change keeps the existing “selection drifted” banner and only logs the upgrade `REASON` to `execution-issues.md`. That repeats the bug’s symptom for the primary interactive path. **Suggested revision:** When `REASON` is the classified CLI-upgrade message, show it in chat on the Step 2 fallback path, not only in `Warnings`. A single visible line with the `npm install -g @openai/codex@latest` guidance is enough; no new flags or subsystems required.

### FINDING_3:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: architecture
- **Location**: skills/implement/references/step2-dispatch.md:41-57
- **Concern**: Step 2 stdout contract still forbids REASON on claude_fallback. Scenario: The plan emits actionable upgrade text as REASON on clean-tree STATUS=claude_fallback and tests that envelope, but the authoritative contract still says REASON is set ONLY when STATUS=bailed. Harnesses and implementers can treat gate fallback REASON as illegal and drop or reject the stdout line.
- **Proposed resolution**: Add ### UPDATED: skills/implement/references/step2-dispatch.md: document optional REASON on claude_fallback for CLI-version gate fallback (sanitized operator message, not a bail token); keep REASON required semantics for STATUS=bailed; sync the mechanical-bail list and edit-in-sync pointers.

### FINDING_4:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/dispatch_step2.py:611-628
- **Concern**: Plan does not order gate detection before dirty-state-after-timeout. Scenario: The current failure path checks porcelain/HEAD/index.lock and can emit REASON=dirty-state-after-timeout before gate classification. A gated Codex launch that also mutates the tree would still hide the upgrade message behind that token, recreating the bug on partial-mutation failures.
- **Proposed resolution**: In dispatch_step2.py plan text, require shared gate detection immediately after each failed Codex attempt and before the dirty-tree retry/bail branch; when a gate is present on a mutating failure, emit STATUS=bailed with the actionable upgrade REASON (forbidden authority), not dirty-state-after-timeout.

### FINDING_5:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/implement/dispatch_step2.py
- **Concern**: Dirty-tree gate path omits required STATUS=bailed. Scenario: The plan says fail closed with forbidden edit authority on HEAD/tree/index-lock changes but never names STATUS=bailed. Implementers may emit STATUS=claude_fallback with forbidden authority, which violates SKILL.md §2.1.5 and becomes orchestrator-envelope-invalid instead of a readable upgrade bail.
- **Proposed resolution**: Explicitly state that mutating gated failures return STATUS=bailed with ORCHESTRATOR_EDIT_AUTHORITY=forbidden and REASON set to the sanitized upgrade message; reserve STATUS=claude_fallback for the clean-tree gate path only.
