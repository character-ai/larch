### OOS_1: [OUT_OF_SCOPE] Dead legacy marker path still omits `CLONE_PATH` stamping
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-edge-cases
- **Severity**: latent
- **Concern**: The dead `run-step-checks.sh` / Step 3 path was intentionally left unchanged, but the legacy `.bg-wait-active` marker block still omits `CLONE_PATH` stamping if that path is ever reactivated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] `bash_probe_target_dir_plausible()` comment drift
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: The comment above `bash_probe_target_dir_plausible()` still describes the old keepalive-only resolver even though the code now uses the marker-local-first chain.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] `_read_keepalive_clone_path()` parser duplication
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: The keepalive clone-path reader is duplicated across Bash and Python helpers, and the parser is slightly weaker than the external runner helper.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.

