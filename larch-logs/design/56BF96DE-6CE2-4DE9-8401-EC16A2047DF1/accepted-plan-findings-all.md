### FINDING_2: Clarify the clean-main contract and failure-mode docs
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-dyn-Entry Gate Integrator
- **Severity**: minor
- **Concern**: `docs/clean-main-contract.md` still under-describes the entry gate by omitting stash requirements and rebase language in the default/standalone summaries and remediation text, and by describing the `USER_PREFIX` path too broadly, so readers can miss what still stays enforced.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add a bullet that local main is rebased onto origin/main (or explicitly say both skills share the existing preflight rebase step) and extend the remediation-path paragraph to cover non-empty stash on an otherwise clean tree
  - From Cursor-Pragmatic: In the planned docs/clean-main-contract.md update, revise section (b) to say branch/main sync is bypassed while working-tree cleanliness and an empty stash list remain required; add stash failure/recovery to section (d) alongside dirty-tree and fetch failures
  - From Cursor-dyn-Entry Gate Integrator: Rewrite the Standalone /design section to require main, clean working tree, and empty git stash list, matching section (a) defaults
  - From Cursor-dyn-Entry Gate Integrator: Extend section (a) with empty stash list; add a stash remediation path in (d); update the line-15 summary to include non-empty stash alongside dirty tree and wrong-branch starts
  - From Cursor-dyn-Entry Gate Integrator: Narrow section (b) to branch-position and main-sync bypass only; state working-tree and stash checks still run on USER_PREFIX/* branches


### FINDING_3: Add stash remediation to session-setup errors
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-dyn-Entry Gate Integrator
- **Severity**: major
- **Concern**: The normalized `session-setup` recovery text in `python/larch/state/bootstrap.py` does not tell operators how to recover from a non-empty stash on a continuation branch, so the error message can point them at the wrong fix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: In `bootstrap.py` `_invoke_error` `session-setup` copy, add an explicit stash-clear remediation (for example `git stash pop` or `git stash drop`) and state that `<USER_PREFIX>/*` bypasses branch/main sync only, not working-tree or stash cleanliness; optionally tailor the normalized text when `PREFLIGHT_ERROR` mentions stash
  - From Cursor-dyn-Entry Gate Integrator: When updating _invoke_error session-setup text, split remediation: uncommitted changes vs non-empty git stash list (pop/drop), and keep USER_PREFIX branch path separate from stash clearing


### FINDING_1:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/state/admission.py
- **Concern**: The unknown-stash branch in the `preflight_main()` spec omits `PREFLIGHT=fail` and `return 2`.. Scenario: The non-empty stash path lists both keys plus exit 2, but the unknown path lists only `PREFLIGHT_ERROR`. An implementer can emit the error and fall through to `git fetch` / sync when stash state is indeterminate, breaking the stated fail-closed contract.
- **Proposed resolution**: Mirror the dirty-tree unknown branch: on `unknown`, emit `PREFLIGHT=fail`, emit the stash unknown `PREFLIGHT_ERROR`, and `return 2` before fetch. ### 1. [correctness] `python/larch/state/admission.py` — complete the unknown-stash fail-closed contract The plan’s non-empty stash branch correctly specifies `PREFLIGHT=fail`, a stash-specific `PREFLIGHT_ERROR`, and `return 2`. The unknown-stash branch lists only `PREFLIGHT_ERROR`. That asymmetry leaves room for preflight to continue into fetch/sync when `git stash list` fails, which contradicts the Approach line “Fail closed if the stash probe itself cannot run.” **Suggested revision:** In the `preflight_main()` update bullets, make the unknown branch match the working-tree unknown path: emit `PREFLIGHT=fail`, emit `PREFLIGHT_ERROR=Could not determine git stash cleanliness. Inspect git stash list and re-run.`, and `return 2` before fetch. --- **Prior-round ledger:** FINDING_2 (`docs/clean-main-contract.md`) and FINDING_3 (`python/larch/state/bootstrap.py`) look fully covered by the firm `UPDATED` sections. FINDING_1 (`skills/design/SKILL.md`) remains `MAY_UPDATE` only; not re-raised after round-1 rejection. OOS_1 and OOS_2 are not re-raised.

