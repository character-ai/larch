# Review Round 2

- Mode: `diff`
- 6 accepted, 3 rejected (3 exonerated)

## Accepted Findings

### FINDING_3: Predictable filtered stdout temp path can be symlinked
- **Reviewer(s)**: codex-specialist-security-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `normalize-issue-env` writes filtered `/larch:issue` stdout to a predictable `$IMPLEMENT_TMPDIR/stall-recovery-issue.stdout.filtered.$$` path using shell redirection, allowing a same-UID symlink precreation attack to truncate or overwrite an arbitrary target.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-security-output.txt: Use mktemp inside the validated tmpdir for the filtered file and clean it up with a trap/local cleanup instead of writing to a predictable $$ path.
  - From codex-specialist-edge-cases-output.txt: Use mktemp inside the tmpdir plus trap cleanup, or parse without a predictable temporary filename.


### FINDING_4: write-failed normalization path can hard-fail and leave stale env
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-bash-kv-output.txt
- **Severity**: important
- **Concern**: On `atomic_write_text` failure, `normalize-issue-env` exits `1` instead of behaving like other soft filing failures, and it may leave a pre-existing `stall-recovery-issue.env` that Step 8 later consumes, risking skipped fallback handling or comments posted to the wrong issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Return exit 0 on write-failed or document stdout-first handling in stall-recovery.md step 4
  - From dyn-bash-kv-output.txt: On `write-failed`, `rm -f "$out_file"` before exiting (mirror `emit_issue_env_false`), and add a harness case that seeds a stale env file then forces `atomic_write_text` failure.


### FINDING_5: Production-token sanitizer harness omits common ship-pr tokens
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: The production-token preservation loop omits `10-head-changed`, `12-head-changed`, and `12-max-retries`, so a future regex regression could map common stall steps to `unknown` without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add missing ship-pr tokens to the case-20 preservation loop


### FINDING_6: Step 4 structure tests do not pin normalize-issue-env wiring
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-bash-kv-output.txt, dyn-issue-batch-output.txt, dyn-prompt-protocol-output.txt
- **Severity**: important
- **Concern**: `test-implement-structure.sh` pins headed issue filing but not the required `normalize-issue-env`, stdout capture, or `ISSUE_ENV_WRITTEN` wiring, so future prose could drop canonical env normalization while CI still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Grep step-4 window for normalize-issue-env and stdout capture wiring
  - From cursor-specialist-testing-output.txt: Add grep -Fq 'normalize-issue-env' (and optionally ISSUE_ENV_WRITTEN / stall-recovery-issue.stdout) inside the stall_step4_window assertions.
  - From dyn-bash-kv-output.txt: Extend the Step 4 awk window with greps for `normalize-issue-env`, `stall-recovery-issue.stdout`, and `ISSUE_ENV_WRITTEN`.
  - From dyn-issue-batch-output.txt: Extend the step-4 `awk` window grep pins (or the dry-run integration block) to require `normalize-issue-env`, `stall-recovery-issue.stdout`, and parsing `ISSUE_ENV_WRITTEN`, mirroring the existing `stall-recovery-issue-input.md` wiring pin.
  - From dyn-prompt-protocol-output.txt: Extend the `stall_step4_window` assertions with greps for `normalize-issue-env`, `stall-recovery-issue.stdout`, and `ISSUE_ENV_WRITTEN` (or `stall-recovery-issue.env`), and note the new pins in `scripts/test-implement-structure.md`.


### FINDING_8: Step 4 does not define ISSUE_RC/stdout capture protocol
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-bash-kv-output.txt, dyn-issue-batch-output.txt, dyn-prompt-protocol-output.txt
- **Severity**: important
- **Concern**: Step 4 calls `normalize-issue-env --issue-exit-code "$ISSUE_RC"` and expects `$IMPLEMENT_TMPDIR/stall-recovery-issue.stdout`, but it does not define how `/larch:issue` stdout is captured or how `ISSUE_RC` is bound. Empty or guessed exit codes can hard-fail normalization or bypass intended failure handling, leaving Step 8 without canonical issue targeting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Document mandatory ISSUE_RC capture from /larch:issue exit status; handle normalize exit 1 like ISSUE_ENV_WRITTEN=false; optionally treat empty --issue-exit-code as invalid input with soft-fail KV emission.
  - From dyn-bash-kv-output.txt: Pin in step 4 that `ISSUE_RC` must be the foreground `/larch:issue` invocation’s process exit code captured in the same Bash block that writes `stall-recovery-issue.stdout`, and add a `test-implement-structure.sh` grep for `normalize-issue-env` plus `--issue-exit-code` alongside the existing `issue-input-file` pins.
  - From dyn-issue-batch-output.txt: In step 4, explicitly require capturing the `/larch:issue` process exit code into `ISSUE_RC` immediately after filing (before `normalize-issue-env`), and make `normalize-issue-env` treat an empty/missing `--issue-exit-code` like a failed filing (`emit_issue_env_false "issue-exit-code-missing"`) with exit **0** so the prose fallback always applies.
  - From dyn-prompt-protocol-output.txt: Add an executable sub-bullet in step 4 mirroring design 5b: invoke `/larch:issue` via Skill, write stdout-only to `$IMPLEMENT_TMPDIR/stall-recovery-issue.stdout`, bind `ISSUE_RC` from the Skill tool exit (with `set +e`/`set -e` if shown as Bash), then call `normalize-issue-env`; or drop the separate exit-code requirement and have `normalize-issue-env` infer failure solely from filtered stdout like `file-design-oos.sh annotate`.


### FINDING_9: Step 4 structure test does not enforce dev-clone gate ordering
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The structure pin checks token presence but not that `is-larch-dev-clone` precedes report composition and `/larch:issue` filing, so a future edit could auto-file from consumer or forked runs while the test still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Compare token positions within stall_step4_window and require is-larch-dev-clone before bug-body/issue-input-file and before the /larch:issue --input-file command.


