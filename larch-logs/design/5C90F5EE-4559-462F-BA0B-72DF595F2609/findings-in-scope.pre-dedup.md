### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: security
- **Location**: scripts/hook-anti-read-poll.sh
- **Concern**: Validate `$state_dir` only after `mkdir -p` and `chmod 700`, so the hardening still dereferences the path before the guard runs.. Scenario: If `$TMPDIR` or an ancestor is symlinked, the pre-check `mkdir -p` and `chmod 700` can act on the attacker-chosen target even though the hook later exits 0. That leaves the unsafe write path and a permission-changing side effect in place.
- **Proposed resolution**: Reject the root chain before any filesystem mutation, or move the directory check ahead of `mkdir -p` and `chmod 700`.



### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: scripts/test-hook-anti-read-poll.sh
- **Concern**: Parent-directory symlink regression setup omits teardown of the existing state directory. Scenario: The shared harness runs several happy-path hook calls first, which creates a real $TMPDIR/larch-read-poll tree; the plan says to replace that path with a symlink but never requires removing the existing directory first, so ln -s can fail and the parent-directory attack is never exercised
- **Proposed resolution**: Add an explicit setup step (rm -rf "$TMPDIR/larch-read-poll" or a fresh TMPDIR for the symlink regressions) before installing the parent symlink and seeding poison state



### FINDING_3:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: security
- **Location**: scripts/hook-anti-read-poll.sh:38-40
- **Concern**: State_dir validation happens after mkdir -p and chmod 700, so a symlinked TMPDIR ancestor can still be redirected and mutated before the guard fires.. Scenario: If TMPDIR or one of its parents points at another writable tree, the hook still creates and chmods the redirected larch-read-poll directory before it exits 0, so the hardening does not close the ancestor-redirection path.
- **Proposed resolution**: Validate a symlink-free TMPDIR base before any filesystem mutation, then derive state_dir from that resolved path.



### FINDING_4:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: security
- **Location**: scripts/hook-anti-read-poll.sh:66-67
- **Concern**: Promotion still uses bare mv into $state_file without a destination-occupation guard.. Scenario: If the leaf path is a directory or symlink-to-directory, mv moves the temp file into that directory instead of replacing the state entry, so the hook loses the counter file and can write into an attacker-chosen tree.
- **Proposed resolution**: Reject non-regular destinations immediately before promotion and only rename over an absent path or plain file.



### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: security
- **Location**: scripts/hook-anti-read-poll.sh
- **Concern**: Promote step still lacks a destination-occupation guard even though Edge cases require directory-like destinations to fail open. Scenario: The hook bullets only say to mv into $state_file to avoid truncation via redirect; if the leaf path is a directory or a symlink whose target is a directory, mv can succeed by dropping the temp file into an attacker-chosen tree instead of replacing the state entry
- **Proposed resolution**: Before promote, skip when [ -d "$state_file" ]; when [ -L "$state_file" ], require readlink target not be a directory (or rm -f the symlink leaf first), then mv; on guard failure rm the temp file and exit 0



### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: security
- **Location**: scripts/hook-anti-read-poll.sh:38-42
- **Concern**: Parent-directory validation is ordered after mkdir/chmod so symlinked $state_dir still gets side effects first. Scenario: The plan requires rejecting a symlinked or non-regular $state_dir before temp creation, but mkdir -p and chmod 700 run first; a preplaced symlink at $TMPDIR/larch-read-poll can be followed for directory creation and permission changes before the guard exits 0
- **Proposed resolution**: Validate [ -d "$state_dir" ] && [ ! -L "$state_dir" ] immediately after binding state_dir and before mkdir -p or chmod; only create/chmod the directory when that check passes



### FINDING_7:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: scripts/test-hook-anti-read-poll.sh
- **Concern**: [SCOPE-REDUCTION] Negative-control scaffolding requires temporarily removing or bypassing the production read guard. Scenario: The positive symlink tests already prove the feature contract. A source-mutating or bypass harness adds restore and platform-skip paths, and a failed restore can leave the hook under test changed during validation.
- **Proposed resolution**: Drop the negative-control bullet. Keep the mandatory positive assertions for no reminder, unchanged poison target, symlink replacement, and fresh row.



### FINDING_8:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: scripts/hook-anti-read-poll.sh:38-57
- **Concern**: [ALREADY_ADDRESSED] state_dir validation is not ordered before state_file read. Scenario: The hook section ties directory validation to temp creation/promotion, but the read block still sits earlier in today's flow. If validation runs only immediately before mktemp, a symlinked `$TMPDIR/larch-read-poll` can still expose a regular poison file under the redirected tree; the read guard will trust it and the parent-dir regression can false-pass or false-fail.
- **Proposed resolution**: Pin hook order explicitly: right after `state_dir` is set (and before `state_file` is read), validate `[ -d "$state_dir" ] && [ ! -L "$state_dir" ]` and exit 0 on failure; only then run `mkdir -p`/`chmod` on a validated path and continue to read/write.



### FINDING_9:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: scripts/hook-anti-read-poll.sh:38-40
- **Concern**: [SCOPE-REDUCTION] mkdir/chmod run before the directory-safety check. Scenario: With a preplaced symlink at `$TMPDIR/larch-read-poll`, `mkdir -p`/`chmod 700` can touch the attacker-chosen target before the planned fail-open exit, adding side effects the issue does not require.
- **Proposed resolution**: Validate `$state_dir` as a non-symlink directory first; call `mkdir -p` and `chmod 700` only when that check passes.



### FINDING_10:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: minor
- **Focus area**: code-quality
- **Location**: <TMPDIR>/plan.txt:47-50
- **Concern**: [SCOPE-REDUCTION] Negative-control scaffolding over-serves the symlink-write fix. Scenario: The required positive regressions already prove the poisoned symlink is not read for the counter and is replaced with a fresh regular state row; adding test-only logic to remove or bypass the guard adds brittle harness complexity without needed coverage
- **Proposed resolution**: Remove the negative-control bullets and the line 71 skip path; keep the poison-row seed, no-reminder assertion, target-unchanged assertion, and observable replacement assertion mandatory



