### OOS_1:
- **Description**: Plan does not mention larch-cleanup-audit.log append. Scenario: Forensics loss on mistaken cleanup attempts; behavior change is low risk but operators lose audit trail
- **Reviewer**: Cursor-Edge
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/cleanup-tmpdir.sh:63-68
- **Phase**: design

### OOS_1:
- **Description**: Inlined larch_design_tmpdir_validate duplicates deferred scripts/lib-design-tmpdir.sh until C3a–c retires ~35 sourcers. Scenario: Validator drift between Python write-design-env and surviving bash design scripts could accept/reject different --design-tmpdir paths across surfaces
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: plan.txt:26-27 scripts/lib-design-tmpdir.sh
- **Phase**: design

### OOS_2:
- **Description**: Prefix-only cleanup allowlist without symlink resolution. Scenario: Current bash is_allowed_tmpdir uses prefix glob without resolving symlinks; a path like /tmp/link where link points outside the tree still passes validation; Python port matching this is parity but retains a pre-existing unsafe-deletion class if callers pass attacker-controlled symlinks
- **Reviewer**: Cursor-Edge
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/cleanup-tmpdir.sh:31-70
- **Phase**: design

### OOS_3:
- **Description**: Prefix-only tmpdir validation allows symlink escape. Scenario: Pre-existing bash accepts paths under /tmp/* without resolving intermediate symlinks; rm -rf can follow a symlink leaf to delete outside the intended tree if a caller passes a crafted path
- **Reviewer**: Cursor-Edge
- **Severity**: latent
- **Focus area**: security
- **Location**: scripts/cleanup-tmpdir.sh:57-70
- **Phase**: design

### OOS_4:
- **Description**: [SCOPE-REDUCTION] finalize.py primitive move is necessary but high-touch. Scenario: Moving cache_sessions_root, read/write_finalize_state*, and FINALIZE_STATE_KEYS in the same PR as 13 new verbs plus ~150 call-site cutovers increases ship-driver regression blast radius without being strictly required for session-setup/read-key/cleanup verbs alone
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: <plan>:63-64;python/finalize.py:628-673
- **Phase**: design

### OOS_5:
- **Description**: Inlined design-tmpdir validator duplicates deferred bash lib. Scenario: Two allowlist implementations can diverge before deferred-lib deletion
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: plan.txt:26;scripts/lib-design-tmpdir.sh
- **Phase**: design

### OOS_6:
- **Description**: Inline _read_session_env_key duplicates future session read-key logic. Scenario: Post-migration two parsers for session-env.sh keys; drift risk only not an F2 cutover blocker
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/run_logs.py:221-237
- **Phase**: design

### OOS_7:
- **Description**: Per-verb emitter table omits which verbs call `quiet_init`. Scenario: Bash also calls `quiet_init` for `read-key`, `entry-gate`, `write-env`, `write-design-env`, `write-id`, and `cleanup-tmpdir`; grouping only `setup`/`write-run-params` under fd-3 may cause a port to skip `quiet_init` on those verbs
- **Reviewer**: Cursor-dyn-bash-parity-contract
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/logging_util.py:52-120
- **Phase**: design

### OOS_1:
- **Description**: [OUT_OF_SCOPE] Inlined lib-design-tmpdir validator duplicates deferred bash lib. Scenario: Until the follow-up issue ports lib-design-tmpdir.sh the Python and bash copies can drift on XDG/TMPDIR allowlist edge cases
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: python/session_env.py:27-27
- **Phase**: design

### OOS_2:
- **Description**: cleanup-tmpdir verb missing from Per-verb emitter routing table despite being one of the 13 ported verbs. Scenario: Success path emits no KV (only larch_err on validation failure); omission may cause an implementer to add spurious success stdout
- **Reviewer**: Cursor-dyn-emitter-routing
- **Severity**: nit
- **Focus area**: correctness
- **Location**: scripts/cleanup-tmpdir.sh:23-70
- **Phase**: design

