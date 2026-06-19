### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: skills/implement/references/ship-pr-exit-matrix.md:21-23
- **Concern**: ship-pr-exit-matrix.md cutover step is garbled and incomplete. Scenario: Plan lines 346-350 only mention replacing git-push.sh and pair it with both cli.py git commit and cli.py push branch. The live doc still calls git-commit.sh at line 21 and git-push.sh at line 23. CI-fix Step 8+ will keep invoking deleted bash after other surfaces move.
- **Proposed resolution**: Rewrite the ship-pr-exit-matrix.md section: replace scripts/git-commit.sh with python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" git commit (line 21) and scripts/git-push.sh with python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" push branch (line 23). Drop the corrupted single-bullet wording.

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: skills/implement/references/ship-pr-exit-matrix.md:21-23
- **Concern**: The `### UPDATED: skills/implement/references/ship-pr-exit-matrix.md` block is garbled: it only names `scripts/git-push.sh` but tells the implementer to substitute both `cli.py git commit` and `cli.py push branch`.. Scenario: The autonomous CI-fix sub-procedure has two distinct steps: step 9 commits via `git-commit.sh` and step 11 pushes via `git-push.sh`. Following the plan text would leave step 9 on the deleted helper and/or mis-apply the push replacement.
- **Proposed resolution**: Split the edit into two explicit replacements: step 9 → `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" git commit -m "Fix CI failure (main-agent)"`; step 11 → `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" push branch`. Update `scripts/test-implement-step8-exit3-first-fixer.sh` needle from `scripts/git-push.sh` to the new push invocation in the same change.

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/cli.py:505-611
- **Concern**: None of the 17 retired `git` verbs or `push branch`/`push force` are in `_MACHINE_STDOUT_KEYS` today; quiet parents such as `merge-pr.sh` and `lib-phantom-probe.sh` source `lib-quiet.sh`.. Scenario: Without registration, inherited quiet routes `emit_kv` contract keys (`PUSHED`, `STATUS`, `COMMITTED`, `SHA`, `PHANTOM_*`, etc.) to fd 3 instead of the subprocess stdout pipe. `merge-pr.sh` command-substitution on force-push recovery then sees empty `PUSHED`/`STATUS` and mis-routes recovery.
- **Proposed resolution**: Keep plan step 3 ordering: add all 19 `(domain, verb)` pairs to `_MACHINE_STDOUT_KEYS` and land `python/test_cli.py` quiet-dispatch coverage before repointing `create-pr.sh`, `merge-pr.sh`, `lib-phantom-probe.sh`, and Python subprocess callers.

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lib-phantom-probe.sh:57-133
- **Concern**: The lib repoint is underspecified for KV shape and side effects: it still calls `check-phantom-dirty.sh`, parses `STATUS=`/`REASON=`, and runs shell-side warning append blocks.. Scenario: After deletion, the call fails. Even a naive swap to `git phantom-probe` without deleting the shell append/parser leaves double warnings (Python `probe_with_warn` already appends) or wrong key parsing (`PHANTOM_STATUS` vs legacy `STATUS=`).
- **Proposed resolution**: Call `python3 "${_phantom_plugin_root}/python/cli.py" git phantom-probe --step "$step_token"` with `--baseline-file` when needed; delete the `STATUS=` parser and shell `append_combined` branches; pass through `PHANTOM_*` keys only. Register `("git","phantom-probe")` in `_MACHINE_STDOUT_KEYS`.

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:439
- **Concern**: Plan lists Step 0 `git-current-branch.sh` prose but not the stale post-dispatch assertion that still names `git-current-branch.sh` vs `BRANCH_NAME`.. Scenario: `step-2-post-dispatch.sh` already emits `BRANCH=` via inline `git symbolic-ref`, not `git-current-branch.sh`. Prose-only path updates leave operators/debuggers chasing a retired helper on the Step 2 branch gate.
- **Proposed resolution**: In the same SKILL edit, replace the `claude_fallback` carve-out with `step-2-post-dispatch.sh` `BRANCH=` vs `BRANCH_NAME` wording (and drop `git-current-branch.sh` there).

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-implement-fence-shape.sh:358-360
- **Concern**: Resume bootstrap harness `fake_run` still matches `git-current-branch.sh`; plan only mentions fence-shape for SKILL literal updates.. Scenario: After `python/bootstrap.py` switches to `python/cli.py git current-branch`, the resume-plan-tail test will not stub the new call and can fail or silently stop exercising branch capture.
- **Proposed resolution**: Extend the `scripts/test-implement-fence-shape.sh` update to stub `python/cli.py git current-branch` (emit `BRANCH=…`) instead of `git-current-branch.sh`.

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/rebase-checkpoint-probe.md:17
- **Concern**: Plan updates `rebase-checkpoint-probe.md` for `git rebase-skip` only; phantom helper docs still name `check-phantom-dirty.sh` / `append-execution-issue.sh`.. Scenario: `lib-phantom-probe.sh` will call `cli.py git phantom-probe`, but the survivor contract doc and `scripts/test-rebase-checkpoint-probe.md` still describe `check-phantom-dirty.sh` sibling stubs, inviting harness drift on the 15+ phantom cases.
- **Proposed resolution**: Add `scripts/rebase-checkpoint-probe.md` and `scripts/test-rebase-checkpoint-probe.md` to the file list; document `lib-phantom-probe.sh` → `python3 "$SCRIPT_DIR/../python/cli.py" git phantom-probe` and stub `python/cli.py` (not `check-phantom-dirty.sh`) in the harness.

### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-implement-structure.sh:203-204
- **Concern**: Structural harness still `require`s `phantom-probe-with-warn.sh --step 8-pre-ship` in `step-8-ship.sh`; plan lists the file generically without these needles.. Scenario: Cutover updates `step-8-ship.sh` to `cli.py git phantom-probe` but leaves `make lint` failing on `test-implement-structure` until an implementer discovers the pins by hand.
- **Proposed resolution**: Flip require/forbid needles to `cli.py git phantom-probe --step 8-pre-ship` and retire the `phantom-probe-with-warn.sh` require line in the same PR.

### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:347-350
- **Concern**: ship-pr-exit-matrix.md update instruction is garbled and omits git-commit.sh. Scenario: The Files section shows only `- scripts/git-push.sh` followed by `with cli.py git commit and cli.py push branch`, conflating two replacements. An implementer can update git-push only, leave git-commit.sh in the autonomous CI-fix steps, and ship a broken /implement Step 8 exit-3 path.
- **Proposed resolution**: Rewrite the ship-pr-exit-matrix entry explicitly: replace `${CLAUDE_PLUGIN_ROOT}/scripts/git-commit.sh` with `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" git commit` (step 9) and `${CLAUDE_PLUGIN_ROOT}/scripts/git-push.sh` with `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" push branch` (step 11).

### FINDING_10:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-implement-structure.sh:203-204
- **Concern**: Files list omits scripts/test-implement-structure.sh even though it hard-requires phantom-probe-with-warn.sh in step-8-ship.sh and is on make test-harnesses-16 via test-implement-structure. Scenario: After step-8-ship.sh is repointed to cli.py git phantom-probe the structure harness still requires phantom-probe-with-warn.sh --step 8-pre-ship and make lint fails despite other surfaces being updated
- **Proposed resolution**: Add ### UPDATED: scripts/test-implement-structure.sh; repoint require()/forbid() checks to cli.py git phantom-probe and refresh ship-pr-exit-matrix.md retired-script assertions; run bash scripts/test-implement-structure.sh in Testing strategy

### FINDING_11:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/references/ship-pr-exit-matrix.md:346-350
- **Concern**: ship-pr-exit-matrix.md edit instruction is garbled: it lists only scripts/git-push.sh but tells the editor to substitute both cli.py git commit and cli.py push branch. Scenario: The autonomous CI-fix sub-procedure needs two distinct replacements (step 9 commit vs step 11 push); a literal read can drop git-commit.sh or map both steps to push branch
- **Proposed resolution**: Rewrite the plan bullet as two explicit replacements: git-commit.sh → python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" git commit -m … and git-push.sh → python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" push branch
