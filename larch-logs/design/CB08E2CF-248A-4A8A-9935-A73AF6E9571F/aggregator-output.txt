### FINDING_1: Invariant-evidence materialization helper is unspecified
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: The plan requires a sanctioned helper to materialize `$IMPLEMENT_TMPDIR/architectural-invariants.md` and its `.identity.env` sidecar, but names no implementation surface, invocation contract, input mapping, output bounds, or identity fields. The referenced files are not currently written by any identified runtime component, so invariant-primary recovery is not implementable from the plan alone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add a firm `### NEW:` or `### UPDATED:` deliverable for the materialization helper (CLI verb or wrapper start hook), document its inputs (`DETAIL`/`DETAIL_FILE` and/or `architectural-invariant-note.md`), outputs, and the exact identity fields written before lane dispatch.
  - From Cursor-Pragmatic: Add a firm `### NEW:` or `### UPDATED:` helper (Python CLI verb or thin wrapper), specify inputs from handoff `DETAIL`/`DETAIL_FILE` and existing invariant note artifacts, and require bounded redacted body bytes plus the `.identity.env` sidecar before wrapper start.
  - From Cursor-Requirements: Add one firm helper surface (for example a `python/cli.py` verb or thin wrapper script), list it under Files to modify/create, and wire ship-pr-ci-fix.md to invoke it with explicit inputs from `NEEDS_USER_REASON` / `DETAIL` / `DETAIL_FILE` and the launch identity fields.

### FINDING_2: Invariant sidecar identity ordering and non-CI run identity are circular
- **Reviewer(s)**: Codex-Arch, Codex-Pragmatic, Codex-Requirements
- **Severity**: major
- **Concern**: The plan requires invariant evidence to contain `TIER`, `ATTEMPT`, and dynamic `STEP` before wrapper start, while wrapper start is also responsible for selecting or emitting those values. It likewise leaves the canonical non-CI `RUN_ID` undefined. This creates a circular launch contract in which evidence cannot be validated before launch and launch cannot proceed without the evidence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Define a two-phase allocation contract that allocates and persists the immutable launch identity before evidence materialization, then launches only after the helper writes and validates the sidecar, or change the sidecar contract so its pre-launch fields are distinct from the post-allocation `STEP`
  - From Codex-Pragmatic: Move evidence materialization into wrapper start after identity selection, define the canonical invariant-only RUN_ID, and atomically write and validate the evidence plus sidecar before launching the lane
  - From Codex-Requirements: Make wrapper start own invariant preparation after it selects the tier, attempt, step, and explicit invariant-mode run identity. Define the stable `RUN_ID` source and require the wrapper or a prepare subcommand to materialize the evidence atomically from the validated handoff `DETAIL` or `DETAIL_FILE` and durable invariant note before launching the lane.

### FINDING_3: Invariant-primary mode lacks an explicit lane, evidence, and run-ID contract
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: The invariant-primary path is not explicitly distinguished from ordinary CI-failure repair. Existing validation still expects a numeric GitHub run ID, run resolution may select an unrelated failed run, CI-log collection remains implicit, and dispatch still expects a failure-log-backed `EvidenceState`. The plan also does not define how invariant-only evidence is passed or how stale evidence is prevented from changing ordinary CI behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Define invariant-primary mode explicitly: bind a documented non-CI `RUN_ID` sentinel in the launch envelope and sidecar; skip `_resolve_run_id` and `_collect_evidence`; omit `--failure-log` or pass a validated invariant-only placeholder; require `--invariant-evidence` only.
  - From Cursor-Requirements: Add an explicit invariant-primary signal (`--invariant-primary` or equivalent) on wrapper start and `ci fixer-lane`, branch lane entry to skip run-id resolution and `_collect_evidence` only on that path, and forbid forwarding optional invariant evidence on ordinary CI-failure tiers.
  - From Cursor-Requirements: Define invariant-primary run identity explicitly (for example bind sidecar `RUN_ID` to `LARCH_RUN_ID` and relax numeric-only validation on that path only), skip PR run-id resolution in wrapper start mode, and add harness coverage for violation-without-`FAILED_RUN_ID`.

### FINDING_4: Failed-run handoff source and conflicting-ID precedence are undefined
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: major
- **Concern**: The plan directs the wrapper to read `MAIN_FAILED_RUN_ID` from a route-exit handoff that does not currently contain it, while the authoritative main-health value is persisted in `main-health.env`. It also does not define precedence or fail-closed behavior when valid `FAILED_RUN_ID` and `MAIN_FAILED_RUN_ID` values coexist but disagree. The wrapper could therefore select the wrong PR or default-branch run and collect unrelated evidence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Read `FAILED_RUN_ID` from `.ship-route-exit-handoff.env` when present; fall back to `MAIN_FAILED_RUN_ID` from `$IMPLEMENT_TMPDIR/main-health.env` (not the route-exit file). Document precedence when both exist and fail closed on malformed values.
  - From Codex-Arch: Specify the accepted relationship between the two fields, including which field applies to PR versus main-branch failures, and fail closed on an unexplained disagreement before tier selection or evidence collection
  - From Codex-Pragmatic: Define route-aware precedence, or fail closed on disagreement, and cover the valid-but-different case in the planned authoritative-handoff fixture
  - From Cursor-Requirements: Specify and implement the real source of truth: read `MAIN_FAILED_RUN_ID` from `main-health.env` (or teach ship route-exit to copy it into the handoff), document precedence when both PR and main run IDs exist, and add a fixture for distinct PR vs main run IDs.
  - From Codex-Requirements: Define route-specific run-ID selection using the handoff reason or an authoritative field. Fail closed on an unexplained disagreement, and add the disagreement case to the mandated handoff integration coverage.

### FINDING_5: Invariant-primary kill-switch behavior is undefined without a failed CI run
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: The plan preserves the existing `LARCH_CI_FIXER=0` inline contract around `FAILED_RUN_ID` and `gh run-logs`, but invariant-primary explicitly permits no failed CI run. The kill-switch path therefore has no defined evidence source or attempt accounting for invariant-only violations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add an invariant-specific kill-switch carve-out: use validated invariant evidence (not `gh run-logs`), define per-violation sentinel/counter paths that do not require `FAILED_RUN_ID`, and forbid the CI-log inline repair shape when only invariant evidence exists.

### FINDING_6: Pre-ship checks repair loops still route failures to main-agent edits
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Concern**: The plan leaves the Step 3, Step 5, and Step 6 repair loops unchanged, including paths that return `NEXT_ACTION=main-agent-edit` after delegated dispatch failure, head changes, or iteration exhaustion. This leaves the required inline-fallback removal incomplete because vendor timeout or failure can still route repair back to main-agent edits instead of continuing through the delegated waterfall.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Specify and implement the required pre-ship retry routing, including fresh next-tier dispatch and bounded exhaustion handling, then update the affected checks-loop contract and focused tests

### FINDING_7: Retry-next-tool does not preserve waterfall lineage after HEAD changes
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Concern**: The plan does not define how a retry after a fixer changes `HEAD` preserves waterfall progress. Because rounds identity is bound to `STARTING_HEAD` and `INPUT_FINGERPRINT`, a fresh start may reject prior rounds as foreign or restart at the first tier rather than selecting the next tool.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Persist a waterfall lineage and attempted-tier set separately from each tier's immutable launch identity, then make the planned multi-tier fixture return retry-next-tool after changing HEAD and verify that the next tier starts exactly once
