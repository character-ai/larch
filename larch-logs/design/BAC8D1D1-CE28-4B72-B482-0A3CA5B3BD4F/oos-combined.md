### OOS_1:
- **Description**: Plan does not mention larch-cleanup-audit.log append. Scenario: Forensics loss on mistaken cleanup attempts; behavior change is low risk but operators lose audit trail
- **Reviewer**: Cursor-Edge
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/cleanup-tmpdir.sh:63-68
- **Phase**: design

### OOS_2:
- **Description**: Inlined larch_design_tmpdir_validate duplicates deferred scripts/lib-design-tmpdir.sh until C3a–c retires ~35 sourcers. Scenario: Validator drift between Python write-design-env and surviving bash design scripts could accept/reject different --design-tmpdir paths across surfaces
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: plan.txt:26-27 scripts/lib-design-tmpdir.sh
- **Phase**: design

### OOS_3:
- **Description**: Prefix-only cleanup allowlist without symlink resolution. Scenario: Current bash is_allowed_tmpdir uses prefix glob without resolving symlinks; a path like /tmp/link where link points outside the tree still passes validation; Python port matching this is parity but retains a pre-existing unsafe-deletion class if callers pass attacker-controlled symlinks
- **Reviewer**: Cursor-Edge
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/cleanup-tmpdir.sh:31-70
- **Phase**: design

### OOS_4:
- **Description**: Prefix-only tmpdir validation allows symlink escape. Scenario: Pre-existing bash accepts paths under /tmp/* without resolving intermediate symlinks; rm -rf can follow a symlink leaf to delete outside the intended tree if a caller passes a crafted path
- **Reviewer**: Cursor-Edge
- **Severity**: latent
- **Focus area**: security
- **Location**: scripts/cleanup-tmpdir.sh:57-70
- **Phase**: design

### OOS_5: Aggregated rollup of 9 capped OOS items
- **Description**: Cap 5 (OOS_ISSUES_PER_RUN_CAP) exceeded; the following 9 items were rolled up by skills/implement/scripts/oos-issue-cap.sh:
  - **OOS_4:**: - **Description**: [SCOPE-REDUCTION] finalize.py primitive move is necessary but high-touch. Scenario: Moving cache_sessions_root, read/write_finalize_state*, and FINALIZE_STATE_KEYS in the same PR as… [Files: finalize.py python/finalize.py:628-673]
  - **OOS_5:**: - **Description**: Inlined design-tmpdir validator duplicates deferred bash lib. Scenario: Two allowlist implementations can diverge before deferred-lib deletion - **Reviewer**: Cursor-Pragmatic - **S… [Files: lib-design-tmpdir.sh plan.txt:26]
  - **OOS_6:**: - **Description**: Inline _read_session_env_key duplicates future session read-key logic. Scenario: Post-migration two parsers for session-env.sh keys; drift risk only not an F2 cutover blocker - **Re… [Files: python/run_logs.py:221-237 session-env.sh]
  - **OOS_7:**: - **Description**: Per-verb emitter table omits which verbs call `quiet_init`. Scenario: Bash also calls `quiet_init` for `read-key`, `entry-gate`, `write-env`, `write-design-env`, `write-id`, and `cl… [Files: python/logging_util.py:52-120]
  - **OOS_1:**: - **Description**: [OUT_OF_SCOPE] Inlined lib-design-tmpdir validator duplicates deferred bash lib. Scenario: Until the follow-up issue ports lib-design-tmpdir.sh the Python and bash copies can drift … [Files: lib-design-tmpdir.sh python/session_env.py:27-27]
  - **OOS_2:**: - **Description**: cleanup-tmpdir verb missing from Per-verb emitter routing table despite being one of the 13 ported verbs. Scenario: Success path emits no KV (only larch_err on validation failure); … [Files: scripts/cleanup-tmpdir.sh:23-70]
  - **OOS_1:**: - **Description**: [OUT_OF_SCOPE] Cleanup allowlist appears to preserve string-prefix root checks for rm -rf. Scenario: Current matcher accepts paths such as /tmp/../... before removal; this is pre-ex… [Files: plan.txt:22-24 scripts/cleanup-tmpdir.sh:35-53]
  - **OOS_2:**: - **Description**: Stale persist-post-plan-keys.sh listed as approved writer. Scenario: Operators misread which writers remain after F2 - **Reviewer**: Cursor-Innovation - **Severity**: latent - **Foc… [Files: AGENTS.md:65 persist-post-plan-keys.sh]
  - **OOS_3:**: - **Description**: [OUT_OF_SCOPE] Inlining the full lib-design-tmpdir.sh validator while keeping the bash lib deferred duplicates ~176 lines that ~35 design scripts still source. Scenario: Validator l… [Files: lib-design-tmpdir.sh python/session_env.py:27-27 scripts/lib-design-tmpdir.sh]
- **Reviewer**: Combined: capped per-run rollup
- **Vote tally**: N/A — capped rollup of 9 entries
- **Phase**: implement

