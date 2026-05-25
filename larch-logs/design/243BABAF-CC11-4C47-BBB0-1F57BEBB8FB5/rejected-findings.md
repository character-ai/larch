### [Plan Review] FINDING_11

### FINDING_11: Branch 2 adopt path should guard issue `STATE` is OPEN before proceeding
- **Reviewer(s)**: Cursor-Edge
- **Severity**: latent
- **Concern**: Plan’s Branch 2 path after `get-issue-state` may not verify `STATE` is `OPEN`; unexpected or partial `jq` output could proceed to adopt while SKILL assumes OPEN-only adopt.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Bail or retry when STATE missing or not OPEN mirroring CLOSED IS_PR handling


### [Plan Review] FINDING_23

### FINDING_23: Avoid hiding `tracking-issue-read` stderr during Branch 1 debugging
- **Reviewer(s)**: Cursor-dyn-stub-output-fidelity
- **Severity**: nit
- **Concern**: Redirecting stderr to `/dev/null` hides sentinel parse / IO errors from operators and logs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-stub-output-fidelity: Remove 2>/dev/null or tee stderr to a tmp log under IMPLEMENT_TMPDIR


### [Plan Review] FINDING_24

### FINDING_24: `larch-log` init harness stub should model full success envelope including `UNCHANGED=true`
- **Reviewer(s)**: Codex-dyn-stub-output-fidelity
- **Severity**: latent
- **Concern**: Real `larch-log.sh init` emits a richer stdout envelope and idempotent `UNCHANGED=true` path; minimal stub may not exercise planned assertions around pre-existing manifest.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-stub-output-fidelity: Add full larch-log init envelope emission; when manifest exists emit UNCHANGED=true and exit 0, and assert no STALL_TRACKING for a pre-existing manifest


### [Plan Review] FINDING_25

### FINDING_25: `get-issue-context` success stub should emit `TITLE_FILE` / `BODY_FILE` keys like production
- **Reviewer(s)**: Codex-dyn-stub-output-fidelity
- **Severity**: latent
- **Concern**: Real success creates files and emits `TITLE_FILE=` / `BODY_FILE=`; silent stub may diverge from contract if later code consumes stdout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-stub-output-fidelity: Have the stub create the two files and emit TITLE_FILE= and BODY_FILE=, even though phase_tracking currently redirects and ignores the output


