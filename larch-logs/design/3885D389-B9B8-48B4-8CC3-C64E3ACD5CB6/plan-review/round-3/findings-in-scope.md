### FINDING_1: Thin wrapper call sites need set +e / set -e fence around substitution
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: Thin wrapper call sites omit `set +e` / `set -e` around command substitution. Under `set -e`, `_inv_out=$(implement-bootstrap-invoke.sh …)` can exit before `_inv_rc=$?`, so exit-2 stderr handling and routing parse never run; dirty-tree recovery and Step 0 abort paths regress.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Preserve the current set +e / _inv_out=… / _inv_rc=$? / set -e fence at every wrapper call site (initial, resume, dirty-tree) and pin it in test-implement-structure.sh

### FINDING_2: Resume-mode wrapper must pass through IMPLEMENT_TMPDIR
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: Resume-mode env contract omits `IMPLEMENT_TMPDIR` pass-through. `implement-bootstrap.sh --resume-plan-tail` selects `resume_existing_tmpdir` only when `IMPLEMENT_TMPDIR` is already exported with `session-env.sh` present; a wrapper that does not inherit/export it before the bootstrap child runs takes the fresh `session-setup` path and breaks dirty-tree resume.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Document IMPLEMENT_TMPDIR as a resume-mode caller export in implement-bootstrap-invoke.md; in resume mode export inherited IMPLEMENT_TMPDIR unchanged before calling implement-bootstrap.sh; add a harness case that pre-exports IMPLEMENT_TMPDIR and asserts the stub/bootstrap child sees the same value

### FINDING_3: Stale Step 0 entrypoints in subskill-invocation.md bypass invoke wrapper
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-dyn-scope-omission
- **Severity**: important
- **Concern**: Shared orchestration docs at `skills/shared/subskill-invocation.md` (lines 77 and 199) still direct agents to run `scripts/implement-bootstrap.sh` (including `--up-to-phase coder`) instead of `implement-bootstrap-invoke.sh`. After the PR retargets `skills/implement/SKILL.md`, grep on `$SKILL_MD` may be clean while `subskill-invocation.md` remains stale—either because verify-only co-update is gated on stale pins in SKILL.md only, or because those bullets were never added to plan scope. Agents following the shared doc bypass the wrapper and the exit-2 stderr contract, contradicting the SKILL.md rewrite.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add an explicit UPDATED entry (or broaden the Approach grep) to retarget those two bullets to implement-bootstrap-invoke.sh --mode initial (bootstrap behavior unchanged underneath)
  - From Cursor-dyn-scope-omission: Add `skills/shared/subskill-invocation.md` to the plan file list (not verify-only); retarget both sentences to `scripts/implement-bootstrap-invoke.sh` (`--mode initial` / envelope parse) per the SKILL.md rewrite

### FINDING_4: test-implement-structure.md sibling documents obsolete Step 0 contract
- **Reviewer(s)**: Cursor-dyn-scope-omission
- **Severity**: important
- **Concern**: Harness contract sibling `scripts/test-implement-structure.md` still documents a single foreground `implement-bootstrap.sh --up-to-phase coder` call in SKILL.md. If the plan updates `scripts/test-implement-structure.sh` pins but omits the `.md` sibling, script-md-siblings drift leaves a false contract for reviewers and future harness edits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-scope-omission: Add `scripts/test-implement-structure.md` to scope (or an explicit bullet under the `test-implement-structure.sh` update) retargeting Step 0 prose to `implement-bootstrap-invoke.sh --mode initial|resume` and absent `_ib_*` helpers
