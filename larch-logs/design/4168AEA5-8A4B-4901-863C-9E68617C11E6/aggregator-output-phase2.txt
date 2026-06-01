Normalized aggregator output from the 16 reviewer slots. Merged where the same behavioral risk and fix family align; kept separate where fixes or code paths differ.

### FINDING_1: `already_merged` in `MergeResult` vs eight `merge-pr.sh` literals
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: `MergeResult` / `merge.py` lists `already_merged` as a ninth merge-pr variant while `test_merge_bash_parity` claims identical classification to `merge-pr.sh`, which documents and emits only eight `MERGE_RESULT` values (no `already_merged`). `already_merged` is set by ship-pr / ci-wait (`ACTION=already_merged`, remapping `version_already_published` when the PR is already `MERGED` in `scripts/ship-pr.sh`), not by `merge-pr.sh`. Parity harness or unit tables will fail, encode a non-bash outcome, or force extra `merge.py` behavior with no bash anchor.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Limit merge.merge_pr to the eight merge-pr.sh literals; treat already_merged as Phase 7 driver/orchestrator state, or exclude it from test_merge_bash_parity and document the split.
  - From Cursor-Edge: Limit merge.py port to merge-pr.sh MERGE_RESULT literals (eight variants). Treat already_merged as Phase 7 driver/state mapping; exclude it from test_merge_bash_parity equivalence
  - From Cursor-Innovation: Limit merge.merge_pr to merge-pr.sh outcomes; drop already_merged from merge.py and the parity table or test it only via a separate ship-pr driver helper

### FINDING_2: Flush-commit recovery predicates vs `merge-pr.sh`
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: The plan’s flush-commit recovery spec only requires `chore(larch-logs):`-prefixed commits, but `scripts/merge-pr.sh:272-285` requires subject prefix `chore(larch-logs): flush `, at most five commits, `larch-logs/`-only paths in the range, and `PR_HEAD_OID` ancestor. A broader prefix allows wrong force-with-lease recovery after rebase or mixed commits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Spell out the four merge-pr.sh predicates in merge.py/config and add parity cases K1/P1/N1/N2a from scripts/test-merge-pr.sh

### FINDING_3: `ensure_pr` push path missing create-pr force-with-lease escalation
- **Reviewer(s)**: Cursor-Edge, Cursor-Innovation
- **Severity**: important
- **Concern**: The `pr.py` push path ports `git-push.sh` only. `create-pr.sh:150-176` escalates to `git-force-push.sh` when push fails on the existing-OPEN-PR fast path. An `ensure_pr` that only retries plain push can leave the remote stale while returning `PR_STATUS=existing`, or fail where bash escalates to force-with-lease.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Mirror create-pr push: on existing PR reuse, retry then force-with-lease via git.force_push_with_lease_expecting; cover in test_pr.py
  - From Cursor-Innovation: Port create-pr push semantics inside pr.py (upstream -u push plus existing-PR NFF recovery); keep push.py for plain git-push.sh call sites only

### FINDING_4: `MergeResult.error` lacks merge diagnostic redaction
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: `merge.py` `MergeResult.error` has no merge diagnostic redaction step. `scripts/merge-pr.sh:54-74` `redact_merge_diagnostic` scrubs `gh` stderr before `ERROR=`; unredacted tokens in `MergeResult.error` can reach logs/state in Phase 7.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Redact and cap merge error text like merge-pr.sh before populating MergeResult.error

### FINDING_5: `RunContext` / APIs omit PR number, state file, and merge result for merge and flush
- **Reviewer(s)**: Cursor-Edge, Cursor-Innovation
- **Severity**: important
- **Concern**: `merge_pr(ctx)` and `flush_logs(ctx)` omit how `PR_NUMBER` and `MERGE_RESULT` are supplied. `RunContext` has no `pr_number` or `state_file` / `merge_result`; `refresh-run-logs.sh` needs `--state-file` for `MERGE_RESULT` and fail-closed skip when the file is missing (`scripts/refresh-run-logs.sh:25-32`). `flush_logs` cannot fail-closed skip after merge without ad hoc state-file parsing unspecified in the plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Extend RunContext or explicit parameters with state_file and pr_number; document flush_logs merge probe including missing-state-file REASON=state-file-missing-fail-closed
  - From Cursor-Innovation: Add merge_result (or state-file reader) to RunContext/flush_logs signature and unit-test merged|admin_merged|already_merged skip paths

### FINDING_6: Fork-aware remote selection beyond cited bash ports
- **Reviewer(s)**: Cursor-Edge
- **Severity**: nit
- **Concern**: `push.py` adds fork-aware origin vs upstream remote selection. `scripts/git-push.sh` and `create-pr.sh` use default/origin push only; extra remote logic is scope beyond the cited port and risks drift unless rebase-push rules are required.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Port git push behavior only (tracking remote/refspec); defer fork remote resolution to Phase 7 driver unless a cited bash caller needs it

### FINDING_7: Flush recovery force-push semantics vs `git-force-push.sh`
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Flush-commit recovery plans `git.force_push_with_lease_expecting` but `merge-pr.sh` calls `git-force-push.sh` with fetch race-retry and `PUSHED=` status (`scripts/merge-pr.sh:290-305`, `scripts/git-force-push.sh:1-14`). Python may report `error` while bash recovers or push with weaker lease semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Port or wrap git-force-push.sh recovery in merge.py; add parity tests for flush-only ahead paths

### FINDING_8: `flush_logs` omits transcript capture and step9a1 manifest steps
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: `flush_logs` omits `refresh-run-logs.sh` steps: `capture-session-transcript` (`scripts/refresh-run-logs.sh:86-95`) and `steps_ran.step9a1` manifest update (`scripts/refresh-run-logs.sh:106-130`). Pre-push refresh drops transcript batch and step9a1 audit flag versus live implement runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Extend flush_logs contract to list and test those sub-steps or document an explicit Phase 7 deferral with parity gap called out

### FINDING_9: `oos.py` `stage_accepted_oos` beyond gate-only bash contract
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: `stage_accepted_oos` files follow-up issues via `gh`; bash Phase 5 only ports `oos-disposition-gate.sh` counting (`skills/implement/scripts/oos-disposition-gate.sh`). Filing stays in `/issue` Step 9a.1; the Python module invents out-of-scope filing logic and drifts from gate-only contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Limit oos.py to disposition_ok parity; defer stage_accepted_oos to Phase 7 or drop it from this bundle

### FINDING_10: Flush recovery five-commit cap omitted from plan edge cases
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: latent
- **Concern**: `merge-pr.sh` caps flush recovery at five commits (`scripts/merge-pr.sh:282`) but plan edge cases omit the cap. Six flush-only commits abort recovery in bash but may pass in Python.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Document and test FLUSH_COUNT le 5 in merge flush-recovery

### FINDING_11: Pre-push clean-tree guard missing from proposed PR push path
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: The proposed PR push path omits the pre-push clean-tree guard from `create-pr.sh` (`scripts/create-pr.sh:122-132`). Uncommitted working-tree fixes can be silently excluded from the pushed PR branch, breaking the documented data-loss guard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Add a minimal git status --porcelain guard before push_branch or ensure_pr pushes, and cover dirty-tree refusal in test_push.py or test_pr.py

### FINDING_12: Single `flush_logs` entrypoint conflates commit-capable pre-merge vs tmpdir-only post-merge
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: `flush_logs` is planned as one entrypoint for pre-push/pre-merge and post-merge, but `refresh-run-logs` includes a git commit while post-merge must be tmpdir-only (`scripts/ship-pr.sh:3587-3592`, `scripts/larch-log.sh:501-508`). Calling a commit-capable flush after merge can trip the post-merge sentinel/default-branch guard or try to create a forbidden post-merge log commit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Split the contract: pre-push/pre-merge may commit logs; post-merge only recovers/updates the tmpdir manifest and final report, with a test proving no git add/commit runs post-merge

---

**Merge notes (for voters, not machine fields):** Sixteen input slots collapsed to twelve findings. `already_merged` (slots 1, 2, 8), create-pr push escalation (4, 9), and RunContext/state-file wiring (6, 12) were merged on shared risk. Flush predicate breadth (3) vs five-commit cap (14), force-with-lease escalation (3/4/9) vs dirty-tree guard (15), and flush predicate spec (2) vs `git-force-push.sh` recovery port (7) stayed separate because fixes or test surfaces differ. No `[OUT_OF_SCOPE]` tags in the supplied input.
