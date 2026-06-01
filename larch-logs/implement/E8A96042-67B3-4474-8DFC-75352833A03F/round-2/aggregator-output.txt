### FINDING_1: [OUT_OF_SCOPE] Routing-envelope parse block is duplicated across Step 0 paths
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, cursor-specialist-security-output.txt, dyn-bootstrap-contract-output.txt, dyn-prompt-orchestration-output.txt
- **Severity**: important
- **Concern**: Initial Step 0 and dirty-tree resume duplicate the routing-envelope parse logic, so future key, merge, or security changes can drift between paths and break resume parity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, cursor-specialist-security-output.txt, dyn-bootstrap-contract-output.txt, dyn-prompt-orchestration-output.txt: Address the concern above.

### FINDING_2: Routing key whitelist lacks a canonical equality/full-key pin
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-harness-wiring-output.txt
- **Severity**: important
- **Concern**: `_inv_routing_keys` / envelope key coverage is duplicated or weakly tested, so adding or removing a routing key in only one place can silently drop required pre-rehydration state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-harness-wiring-output.txt: Address the concern above.

### FINDING_3: Wrapper internal names still use stale `_ib_*` prefix
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Wrapper-local helpers still use `_ib_*` names after SKILL-side helpers were removed, which can confuse future maintainers and searches.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: Success harness does not require `bootstrap-routing.env` in all success paths
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-harness-wiring-output.txt
- **Severity**: latent
- **Concern**: Tests skip or omit file assertions, so a regression that stops writing `bootstrap-routing.env` can pass while file-first orchestrator parsing breaks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, dyn-harness-wiring-output.txt: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] Exit-2 handler lacks coverage/default for some `STEP_FAILED` values
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-bootstrap-contract-output.txt
- **Severity**: latent
- **Concern**: Several bootstrap exit-2 failures can exit silently with no operator stderr because the wrapper case statement has no default or arms for all emitted `STEP_FAILED` tokens.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-bootstrap-contract-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] Harness copies `lib-quiet` only for current redact dependency chain
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The sandbox stub layout may become incomplete if redact helper dependencies grow.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: Dirty-tree resume can retain stale routing values when file parse is skipped
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-prompt-orchestration-output.txt
- **Severity**: latent
- **Concern**: Resume parsing uses fill-if-empty stdout fallback and insufficient unsets, so skipped/unreadable `bootstrap-routing.env` can leave stale bail/branch routing state after a successful resume.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, dyn-prompt-orchestration-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] Non-2 wrapper failures fall through to routing parse
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-portability-output.txt, dyn-bootstrap-contract-output.txt
- **Severity**: important
- **Concern**: SKILL call sites only special-case exit 2; exit 1 or other non-zero wrapper failures can still parse empty/partial stdout and continue with unset routing state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-portability-output.txt, dyn-bootstrap-contract-output.txt: Address the concern above.

### FINDING_9: Wrapper harness lacks non-2 exit-code propagation coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Tests do not verify wrapper propagation of bootstrap exit codes other than 2, so exit-code remapping could go undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_10: Missing tests for `SESSION_ENV_PATH` and `ISSUE_NUMBER` argv fallbacks
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Fallback wiring for caller env and issue number can regress without a harness failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: Missing absent pins for removed `_ib_*` helpers
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-harness-wiring-output.txt
- **Severity**: nit
- **Concern**: Structural tests do not forbid reintroducing `_ib_handle_bootstrap_exit2` or `_ib_kv_scan` helper definitions/calls.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-harness-wiring-output.txt: Address the concern above.

### FINDING_12: `--coder` absence check is substring-fragile
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The harness can falsely fail if future `--coder-*` flags appear.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] Redaction-failure stderr branches are untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: If redact helpers fail, fallback operator messages may regress without test coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] Wrapper harness is stub-only
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Wrapper/bootstrap integration bugs require other harnesses or manual runs because this harness stubs bootstrap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] Unquoted `IMPLEMENT_TMPDIR` assignment in wrapper exit-2 handler
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-bash-portability-output.txt
- **Severity**: latent
- **Concern**: `IMPLEMENT_TMPDIR=$_ib_tmpdir` can break or misdirect log checks when the tmpdir contains spaces or shell-sensitive characters.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-bash-portability-output.txt: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] `bootstrap-routing.env` file-first read has limited hardening
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: The read path checks `-f` and `! -L` but does not fully harden against local TOCTOU/path-canonicalization threats.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] Some exit-2 diagnostics are emitted without redaction
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-redaction-boundary-output.txt
- **Severity**: nit
- **Concern**: Several exit-2 arms print diagnostic KV lines directly to stderr, which can expose unredacted diagnostic material by design/pre-existing behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, dyn-redaction-boundary-output.txt: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] Pre-existing unquoted `IMPLEMENT_TMPDIR` assignment remains in bootstrap
- **Reviewer(s)**: dyn-bash-portability-output.txt
- **Severity**: nit
- **Concern**: `scripts/implement-bootstrap.sh` still has a pre-existing unquoted `IMPLEMENT_TMPDIR=$SESSION_TMPDIR` assignment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-portability-output.txt: Address the concern above.

### FINDING_19: Dirty-tree resume can clobber preserved `coder` state with empty resume-envelope values
- **Reviewer(s)**: dyn-routing-envelope-output.txt
- **Severity**: important
- **Concern**: Resume parse unconditionally applies all routing keys from `bootstrap-routing.env`, but resume-tail bootstrap can emit empty `coder`/`coder_fallback`, overwriting orchestrator state needed for Step 2 routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-routing-envelope-output.txt: Address the concern above.

### FINDING_20: Success-path write follows `bootstrap-routing.env` symlinks
- **Reviewer(s)**: dyn-redaction-boundary-output.txt
- **Severity**: important
- **Concern**: The wrapper writes `bootstrap-routing.env` with shell redirection and no symlink guard, allowing a planted symlink in the tmpdir to clobber another writable path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-redaction-boundary-output.txt: Address the concern above.

### FINDING_21: Step 0 prose can be read as multiple bootstrap invocations
- **Reviewer(s)**: dyn-prompt-orchestration-output.txt
- **Severity**: latent
- **Concern**: Multiple imperative references to running `implement-bootstrap-invoke.sh --mode initial` can lead a literal agent to invoke bootstrap outside the single Step 0 owner block.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-orchestration-output.txt: Address the concern above.

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

### FINDING_25: [OUT_OF_SCOPE] SKILL rehydration prose still names raw bootstrap script
- **Reviewer(s)**: dyn-prompt-orchestration-output.txt
- **Severity**: nit
- **Concern**: A rehydration line still points at `implement-bootstrap.sh --resume-plan-tail` instead of the invoke wrapper surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-orchestration-output.txt: Address the concern above.

### FINDING_26: [OUT_OF_SCOPE] Linting docs omit new invoke harness target
- **Reviewer(s)**: dyn-harness-wiring-output.txt
- **Severity**: nit
- **Concern**: `docs/linting.md` documents the older bootstrap harness but not the new `test-implement-bootstrap-invoke` target.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-wiring-output.txt: Address the concern above.
