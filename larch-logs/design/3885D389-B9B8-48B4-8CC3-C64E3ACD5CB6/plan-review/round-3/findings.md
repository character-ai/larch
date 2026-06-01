### FINDING_1:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:492-498
- **Concern**: Thin wrapper call sites omit set +e/set -e guard around command substitution. Scenario: Under set -e, _inv_out=$(implement-bootstrap-invoke.sh …) exits before _inv_rc=$?, so exit-2 stderr handling and routing parse never run; dirty-tree recovery and Step 0 abort paths regress
- **Proposed resolution**: Preserve the current set +e / _inv_out=… / _inv_rc=$? / set -e fence at every wrapper call site (initial, resume, dirty-tree) and pin it in test-implement-structure.sh

### FINDING_2:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/implement-bootstrap-invoke.sh (NEW) / skills/implement/scripts/test-implement-bootstrap-invoke.sh (NEW)
- **Concern**: Resume-mode env contract omits IMPLEMENT_TMPDIR pass-through. Scenario: implement-bootstrap.sh --resume-plan-tail selects resume_existing_tmpdir only when IMPLEMENT_TMPDIR is already exported with session-env.sh present; a wrapper that does not inherit/export it before the bootstrap child runs takes the fresh session-setup path and breaks dirty-tree resume
- **Proposed resolution**: Document IMPLEMENT_TMPDIR as a resume-mode caller export in implement-bootstrap-invoke.md; in resume mode export inherited IMPLEMENT_TMPDIR unchanged before calling implement-bootstrap.sh; add a harness case that pre-exports IMPLEMENT_TMPDIR and asserts the stub/bootstrap child sees the same value

### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/shared/subskill-invocation.md:77,199
- **Concern**: Verify-only co-update is gated on stale pins in SKILL.md only. Scenario: After SKILL retargets to implement-bootstrap-invoke.sh, grep on $SKILL_MD will be clean and subskill-invocation.md will still tell orchestrators to run implement-bootstrap.sh --up-to-phase coder directly, bypassing the wrapper and exit-2 stderr contract
- **Proposed resolution**: Add an explicit UPDATED entry (or broaden the Approach grep) to retarget those two bullets to implement-bootstrap-invoke.sh --mode initial (bootstrap behavior unchanged underneath)

### FINDING_4:
- **Reviewer(s)**: Cursor-dyn-scope-omission
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/shared/subskill-invocation.md:77,199
- **Concern**: Stale Step 0 entrypoints still name prompt-side `scripts/implement-bootstrap.sh --up-to-phase coder` (line 77 omits phase flag but still points at bootstrap, not the invoke wrapper). Scenario: After the PR, shared orchestration docs contradict `skills/implement/SKILL.md` and re-teach the removed inline harness; agents following subskill-invocation.md bypass `implement-bootstrap-invoke.sh`
- **Proposed resolution**: Add `skills/shared/subskill-invocation.md` to the plan file list (not verify-only); retarget both sentences to `scripts/implement-bootstrap-invoke.sh` (`--mode initial` / envelope parse) per the SKILL.md rewrite

### FINDING_5:
- **Reviewer(s)**: Cursor-dyn-scope-omission
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-implement-structure.md:9-11
- **Concern**: Harness contract sibling still documents one foreground `implement-bootstrap.sh --up-to-phase coder` call in SKILL.md. Scenario: Plan rewrites `scripts/test-implement-structure.sh` pins but omits the `.md` sibling; script-md-siblings drift leaves a false contract for reviewers and future harness edits
- **Proposed resolution**: Add `scripts/test-implement-structure.md` to scope (or an explicit bullet under the `test-implement-structure.sh` update) retargeting Step 0 prose to `implement-bootstrap-invoke.sh --mode initial|resume` and absent `_ib_*` helpers
