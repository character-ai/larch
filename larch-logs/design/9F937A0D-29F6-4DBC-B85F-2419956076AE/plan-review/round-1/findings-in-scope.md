Normalizing reviewer findings into a merged list. Checking key source locations to align concerns with the codebase.
Normalized aggregator output from the 15 raw reviewer slots (merged by shared behavioral risk; severity uses **important** > **latent** > **nit**).

### FINDING_1: Unguarded `set -euo pipefail` breaks the checkpoint 0/1/2 contract
- **Reviewer(s)**: Cursor-Arch, Codex-Innovation, Codex-Pragmatic, Codex-dyn-extraction-parity, Codex-dyn-harness-matrix
- **Severity**: important
- **Concern**: A planned `oos-disposition-checkpoint.sh` with global `set -euo pipefail` conflicts with the inline Step 8+ fence in `skills/implement/SKILL.md` (lines 1193–1282), which tolerates fallible state/git/session-id/ndjson probes (`2>/dev/null || true`, `set +e` only around the gate). Unguarded `git rev-parse`, `git merge-base`, `grep`, `find`, or missing optional artifacts can abort the helper with shell rc 1/127 before the gate runs and before deliberate validation paths can log exit 2 via `append-tool-failure.sh`, breaking the intended 0/1/2 branch contract and Step 8+ remediation semantics (including HEAD / `origin/main..HEAD` fallback when merge-base is absent or git context is partial).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Mirror the fence: keep input resolution under set +e (or explicit || true/-f guards on every fallible step), then set +e only around the gate call; drop global pipefail unless every pipeline is audited like the inline block
  - From Codex-Innovation: Preserve the current tolerant wrappers from skills/implement/SKILL.md:1201-1218: use 2>/dev/null || true for git rev-parse, merge-base, session-id reads, and find pipeline probes, then convert intended validation failures to logged exit 2
  - From Codex-Pragmatic: Add explicit || true guards around every optional probe/pipeline, especially the grep state reads, session-id read, merge-base, and find fallback, while keeping validation failures on the deliberate logged exit-2 paths
  - From Codex-dyn-extraction-parity: Require the helper to keep the current guarded semantics: initialize defaults, use 2>/dev/null || true on git/session/find probes, tolerate absent state keys as false, then apply the existing ndjson precondition and gate call
  - From Codex-dyn-harness-matrix: Specify the current 2>/dev/null || true guards for git rev-parse and git merge-base in the helper, and add one checkpoint harness case for origin/main present with no merge-base

### FINDING_2: Direct-path invocation without pinned executable mode
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Codex-Pragmatic
- **Severity**: important
- **Concern**: The plan invokes the new checkpoint by direct path, but does not require mode `100755` or a `bash` wrapper. If `oos-disposition-checkpoint.sh` lands as `0644`, Step 8+ gets permission denied (shell rc 126) before the helper runs or logs via `append-tool-failure.sh`, bypassing the promised 0/1/2 contract and audit trail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Commit oos-disposition-checkpoint.sh as executable 100755 or invoke it through bash; keep the harness aligned with the runtime invocation
  - From Codex-Edge: Specify the mode/call contract: either add the executable bit and have the harness invoke CHECKPOINT directly, or invoke it with bash consistently from SKILL.md and tests
  - From Codex-Pragmatic: Specify git mode 100755 and add a minimal [ -x "$CHECKPOINT" ] assertion/direct-path invocation in the existing harness, or invoke it via bash in SKILL.md and tests

### FINDING_3: Pre-gate failures lack a stable `--output-file` for `append-tool-failure.sh`
- **Reviewer(s)**: Cursor-Edge, Cursor-Pragmatic, Cursor-dyn-harness-matrix
- **Severity**: important
- **Concern**: Decision 2 routes all non-zero checkpoint exits through `append-tool-failure.sh`, which requires an existing `--output-file` (`scripts/append-tool-failure.sh:100-104`). Pre-gate paths (ambiguous ndjson, missing ndjson precondition, CLI usage) never invoke the gate, so `oos-disposition-gate.stderr.log` may be missing or stale; `append-tool-failure.sh` then exits 2 on a missing file, which under `set -e` can prevent returning the intended checkpoint rc 2 and makes harness assertions on `execution-issues.md` flaky.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Tee pre-gate/CLI errors to a dedicated <implement-tmpdir>/oos-disposition-checkpoint.stderr.log (touch if needed, per step-7a.sh:43) and pass that path to append-tool-failure; only use the gate stderr log after gate invocation
  - From Cursor-Pragmatic: Mirror gate failures: tee pre-gate/usage diagnostics into <implement-tmpdir>/oos-disposition-gate.stderr.log (or a checkpoint diag file) before append; document the path in oos-disposition-checkpoint.md
  - From Cursor-dyn-harness-matrix: Specify a single implement-tmpdir diag path (e.g. oos-disposition-checkpoint.stderr.log): tee pre-gate stderr there before append-tool-failure; document it in oos-disposition-checkpoint.md

### FINDING_4: Harness does not assert exit-1 logging to `execution-issues.md`
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The planned checkpoint tests validate disposition-gap rc behavior but not that exit 1 (real OOS disposition gap) produces a `Tool Failures` entry. A helper could return 1 without logging `site step-8-oos-checkpoint` / `tool oos-disposition-checkpoint.sh`, regressing the audit trail while still passing rc-only tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add a minimal assertion to the existing disposition-gap checkpoint case that fake execution-issues.md contains a Tool Failures entry with site step-8-oos-checkpoint and tool oos-disposition-checkpoint.sh; keep the existing exit-2 log assertions.

### FINDING_5: `append-tool-failure.sh` must stay best-effort so the captured checkpoint rc is preserved
- **Reviewer(s)**: Codex-dyn-extraction-parity, Codex-dyn-harness-matrix
- **Severity**: important
- **Concern**: The inline fence ends logging with `|| true` before `exit` (`skills/implement/SKILL.md:1273-1281`). If the extracted helper calls `append-tool-failure.sh` under `set -e` without that guard, logging failures (missing output file, redaction/write errors per `scripts/append-tool-failure.sh:100-130`) can override the saved gate or validation rc 1/2, breaking the helper’s 0/1/2 contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-extraction-parity: After capturing the original failure rc, call append-tool-failure.sh with || true and always exit the captured rc; keep the proposed site tokens unchanged
  - From Codex-dyn-harness-matrix: Add the current || true pattern inside the helper after saving the original rc, then always exit the saved rc

### FINDING_6: NEVER #17/#18 prose can drift from the checkpoint entrypoint
- **Reviewer(s)**: Codex-dyn-harness-matrix
- **Severity**: latent
- **Concern**: The plan keeps NEVER #17/#18 wording even though #18 still names direct `oos-disposition-gate.sh` invocation as the required Step 8+ action. After extraction, maintainers may bypass the checkpoint helper’s input plumbing and logging, weakening the load-bearing invariant.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-harness-matrix: Minimally update NEVER #17/#18 to say the Step 8+ checkpoint helper invokes the gate and owns gate failure logging, while preserving the OOS_PENDING and run-statistics invariants
