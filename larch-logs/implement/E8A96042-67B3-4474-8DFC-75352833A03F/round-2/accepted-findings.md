### FINDING_10: Missing tests for `SESSION_ENV_PATH` and `ISSUE_NUMBER` argv fallbacks
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Fallback wiring for caller env and issue number can regress without a harness failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_12: `--coder` absence check is substring-fragile
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The harness can falsely fail if future `--coder-*` flags appear.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_19: Dirty-tree resume can clobber preserved `coder` state with empty resume-envelope values
- **Reviewer(s)**: dyn-routing-envelope-output.txt
- **Severity**: important
- **Concern**: Resume parse unconditionally applies all routing keys from `bootstrap-routing.env`, but resume-tail bootstrap can emit empty `coder`/`coder_fallback`, overwriting orchestrator state needed for Step 2 routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-routing-envelope-output.txt: Address the concern above.


### FINDING_2: Routing key whitelist lacks a canonical equality/full-key pin
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-harness-wiring-output.txt
- **Severity**: important
- **Concern**: `_inv_routing_keys` / envelope key coverage is duplicated or weakly tested, so adding or removing a routing key in only one place can silently drop required pre-rehydration state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-harness-wiring-output.txt: Address the concern above.


### FINDING_20: Success-path write follows `bootstrap-routing.env` symlinks
- **Reviewer(s)**: dyn-redaction-boundary-output.txt
- **Severity**: important
- **Concern**: The wrapper writes `bootstrap-routing.env` with shell redirection and no symlink guard, allowing a planted symlink in the tmpdir to clobber another writable path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-redaction-boundary-output.txt: Address the concern above.


### FINDING_22: Invoke contract omits actual routing-envelope merge semantics
- **Reviewer(s)**: dyn-prompt-orchestration-output.txt
- **Severity**: latent
- **Concern**: Documentation says file-first re-parse but does not specify overwrite/fill-only behavior, symlink refusal, or dirty-tree state-clearing requirements.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-orchestration-output.txt: Address the concern above.


### FINDING_23: Initial-mode success harness does not assert wrapper rc
- **Reviewer(s)**: dyn-harness-wiring-output.txt
- **Severity**: latent
- **Concern**: Success tests use `|| true` and can pass argv checks even if the wrapper exits non-zero.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-wiring-output.txt: Address the concern above.


### FINDING_24: Resume-mode success coverage does not check file envelope
- **Reviewer(s)**: dyn-harness-wiring-output.txt
- **Severity**: latent
- **Concern**: Resume tests check argv/env and one stdout key but not `bootstrap-routing.env` existence or required contents.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-wiring-output.txt: Address the concern above.


### FINDING_4: Success harness does not require `bootstrap-routing.env` in all success paths
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-harness-wiring-output.txt
- **Severity**: latent
- **Concern**: Tests skip or omit file assertions, so a regression that stops writing `bootstrap-routing.env` can pass while file-first orchestrator parsing breaks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, dyn-harness-wiring-output.txt: Address the concern above.


### FINDING_7: Dirty-tree resume can retain stale routing values when file parse is skipped
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-prompt-orchestration-output.txt
- **Severity**: latent
- **Concern**: Resume parsing uses fill-if-empty stdout fallback and insufficient unsets, so skipped/unreadable `bootstrap-routing.env` can leave stale bail/branch routing state after a successful resume.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, dyn-prompt-orchestration-output.txt: Address the concern above.


### FINDING_9: Wrapper harness lacks non-2 exit-code propagation coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Tests do not verify wrapper propagation of bootstrap exit codes other than 2, so exit-code remapping could go undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


