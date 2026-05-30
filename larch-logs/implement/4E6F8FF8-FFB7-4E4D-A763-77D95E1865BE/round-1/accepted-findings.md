### FINDING_13: Option A backstop message misleading when follow-up fails closed at Step 5
- **Reviewer(s)**: dyn-follow-up-commit-flow-output.txt
- **Severity**: important
- **Concern**: On the round-mode follow-up path in `skills/review-and-fix/scripts/review-and-fix.sh:467-480`, a failed `git add -A` / `git-commit.sh` emits “leaving residue for the ship-pr Option A backstop”, but when tracked porcelain remains non-empty the next check returns exit **2** with `CODER_STATUS=failed` and no `CODER_COMMIT_SHA`. `review-and-fix.md` documents exit **2** as blocking for `/implement` Step 5, while Option A only runs later in `ship-pr.sh` `run_rebase_rebump`; in persistent-hook failure class the workflow stops at Step 5, so the backstop message describes a recovery path that does not run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-follow-up-commit-flow-output.txt: Reword or gate the Option A warning so it only logs when execution can actually reach `run_rebase_rebump` (e.g. findings mode / warn-and-continue), or drop it on the fail-closed branch and rely on the second `left tracked changes uncommitted after follow-up` message; align `review-and-fix.md` with whichever contract you keep.


### FINDING_6: Pre-rebase `git add -u` auto-commit stages all tracked dirty paths (`ship-pr.sh`)
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-rebase-fixup-commit-scope-output.txt
- **Severity**: important
- **Concern**: In `scripts/ship-pr.sh` Step 0b (~2853–2870 / ~2856–2870), when porcelain is non-empty, `run_rebase_rebump` runs `git add -u` on every tracked dirty path and commits via `git-commit.sh` (`chore: pre-rebase working-tree fixup (#3209)`). Failures are warnings only until `drop-bump-commit.sh` Guard 1. That commit survives rebase (tests at `scripts/test-ship-pr.sh:656-660` expect it). Any unintended tracked WIP—including credentials/tokens left modified during `/implement`—can be permanently recorded on the PR branch, not merely unstaged.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Restrict auto-commit to an allowlisted path set (e.g. larch-logs/ only) or fail closed when staged diff matches secret/forbidden-path policies.
  - From cursor-specialist-edge-cases-output.txt: consider scoping the add/commit to known larch-logs paths or failing closed.
  - From dyn-rebase-fixup-commit-scope-output.txt: Narrow staging to an allowlist (e.g. `larch-logs/`, known hook targets) or require a clean tracked tree except explicitly documented paths; alternatively gate the fixup on residue class (hook vs. other) before `git add -u`.


### FINDING_9: No mixed octal-then-valid duplicate fixture for `block_len`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: At `skills/design/scripts/test-trailer-awk.sh:94-101`, there is no fixture where rejected octal lines precede a valid trailer. A regression counting rejected octal lines toward `block_len` passes `octal-rejected` (`block_len` 0) but breaks plan-size when a valid trailer follows an `08`/`09` line.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add diff_added: 08 then diff_added: 5 before diff_lines:; assert parse block_len 1, value 5, and empty keys for the octal line alone.


