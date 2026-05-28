### FINDING_1: Session Setup structural pins are incomplete
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Session Setup structural checks still use an overly broad Step 0 span and omit planned pins/greps. Future edits could add extra bootstrap fences or reintroduce stubs without failing `test-implement-structure`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_11: Explicit codex-unavailable harness coverage is missing
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The explicit `--coder=codex` unavailable case is not covered. Codex unavailability could regress while cursor-only tri-state cases still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_12: Step 2 cursor-present gate can silently override bootstrap selection
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Step 0 can select Cursor, but Step 2 can see `CURSOR_PRESENT=false` and silently fall back to Claude, bypassing the bootstrap `coder_fallback` semantics and warning model.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_13: copy-plan and gh-issue-view redaction handlers fail open
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Exit-2 handlers for `copy-plan` and `gh-issue-view` can print raw stderr if the redaction pipeline fails, potentially exposing tokens or sensitive issue/body content in the operator transcript.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_2: Missing missing-plan coder-selection harness case
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The plan-required `B16-coder-skip-missing-plan` coverage is absent. A regression could emit `coder=` without `plan.txt` on a non-`REPO_UNAVAILABLE` path and silently break Step 2 dispatch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_3: Dirty-tree resume-tail recovery lost main Step 0 semantics
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The dirty-tree resume-tail fence was collapsed too far and no longer mirrors the main Step 0 recovery path. Resume can lose operator gating, clean-tree recheck, `CLAUDE_PLUGIN_ROOT` recovery, `--coder` / `--caller-env` / fork argv parity, KV re-parse, or stale bail-state handling, causing wrong routing or blocked Step 2 execution.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_4: Changelog still documents old Codex-first omitted-coder default
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `CHANGELOG.md` still says `/implement` Step 0 defaults to Codex-first, contradicting the Phase 4 Cursor-first routing behavior. Release notes and runtime behavior now disagree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_5: SECURITY.md lost implementer trust-boundary detail
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: The external tool delegation security text was compressed enough to remove material trust-boundary guarantees and dispatcher validation details, including protected-path, submodule, history, and `git add -A` scope-drift mitigations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt: Address the concern above.


### FINDING_9: Step 2.4 claude_fallback warning logic is incomplete
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Step 2.4 warning branches still have duplicate or imprecise unavailable wording and do not fully align with the Step 0 `coder_fallback` / explicit `--coder` semantics. Operators may see misleading or duplicated warnings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt: Address the concern above.


