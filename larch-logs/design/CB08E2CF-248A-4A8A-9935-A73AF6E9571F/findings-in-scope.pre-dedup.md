### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: architecture
- **Location**: skills/implement/references/ship-pr-ci-fix.md
- **Concern**: Invariant evidence materialization helper is unspecified. Scenario: The plan requires a single sanctioned helper to write `$IMPLEMENT_TMPDIR/architectural-invariants.md` and `.identity.env` before each invariant-tier start, but no firm file names a script, wrapper mode, or `python/cli.py` verb that performs that write. Only `ci_fixer_lane.py` consumes the path; nothing in the repo creates it today. Invariant-primary `ci-fix` cannot run.
- **Proposed resolution**: Add a firm `### NEW:` or `### UPDATED:` deliverable for the materialization helper (CLI verb or wrapper start hook), document its inputs (`DETAIL`/`DETAIL_FILE` and/or `architectural-invariant-note.md`), outputs, and the exact identity fields written before lane dispatch.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/ci_fixer_lane.py
- **Concern**: Invariant-primary lane contract omits RUN_ID and failure-log binding. Scenario: The plan says invariant-primary may proceed without `FAILED_RUN_ID` and must skip CI-log collection, but the lane still requires a numeric `--run-id`, hashes it into the dynamic `STEP`, stores it in `fixer-rounds.tsv`, and `_dispatch` always passes `--failure-log` from `_collect_evidence`. On a green PR with `NEEDS_USER_REASON=architectural-invariants-violation` and no failed run, start/finalize identity and launcher argv are undefined and can close-fail or launch with stale CI evidence.
- **Proposed resolution**: Define invariant-primary mode explicitly: bind a documented non-CI `RUN_ID` sentinel in the launch envelope and sidecar; skip `_resolve_run_id` and `_collect_evidence`; omit `--failure-log` or pass a validated invariant-only placeholder; require `--invariant-evidence` only.



### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/implement/scripts/step-8-ci-fixer.sh
- **Concern**: MAIN_FAILED_RUN_ID is read from the wrong handoff surface. Scenario: The plan tells the wrapper to read `MAIN_FAILED_RUN_ID` from `.ship-route-exit-handoff.env`, but route-exit only maps `failed_run_id` to `FAILED_RUN_ID` and never writes `MAIN_FAILED_RUN_ID` there. Preflight/bootstrap persists `MAIN_FAILED_RUN_ID` in `$IMPLEMENT_TMPDIR/main-health.env` (see `step2-main-health-fix.md`). When PR and default-branch runs diverge or `FAILED_RUN_ID` is empty, the wrapper can miss the authoritative main-health run and re-resolve the wrong CI run.
- **Proposed resolution**: Read `FAILED_RUN_ID` from `.ship-route-exit-handoff.env` when present; fall back to `MAIN_FAILED_RUN_ID` from `$IMPLEMENT_TMPDIR/main-health.env` (not the route-exit file). Document precedence when both exist and fail closed on malformed values.



### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/implement/references/ship-pr-ci-fix.md
- **Concern**: Kill-switch inline path is undefined for invariant-primary without FAILED_RUN_ID. Scenario: The rewritten procedure keeps `LARCH_CI_FIXER=0` on the existing `main-agent-ci-fix-$FAILED_RUN_ID` and `gh run-logs --run-id "$FAILED_RUN_ID"` contract, while the new invariant-primary branch is ordered first and explicitly allows no failed CI run. With the kill switch enabled on that path, operators get no defined evidence source or attempt accounting.
- **Proposed resolution**: Add an invariant-specific kill-switch carve-out: use validated invariant evidence (not `gh run-logs`), define per-violation sentinel/counter paths that do not require `FAILED_RUN_ID`, and forbid the CI-log inline repair shape when only invariant evidence exists.



### FINDING_5:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/checks_lint_fix.py:278-311
- **Concern**: The plan explicitly leaves the Step 3, Step 5, and Step 6 repair loops unchanged, including paths that return `NEXT_ACTION=main-agent-edit` after delegated dispatch failure, head changes, or iteration exhaustion. Scenario: This feature's required inline-fallback removal is incomplete: a vendor timeout or failure on a pre-ship checks path still routes repair back to main-agent edits instead of retrying the delegated waterfall before any sanctioned exception
- **Proposed resolution**: Specify and implement the required pre-ship retry routing, including fresh next-tier dispatch and bounded exhaustion handling, then update the affected checks-loop contract and focused tests



### FINDING_6:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: architecture
- **Location**: <TMPDIR>/plan.txt:20-24,38-40,62-72
- **Concern**: The invariant-evidence protocol requires `STEP` in the sidecar before each tier start, but the plan also makes the wrapper start invocation the operation that allocates and emits the dynamic `STEP`. Scenario: The prescribed order is circular: evidence must be materialized before start, while its required identity cannot be completed until start emits `STEP`; an implementation must either derive or reuse a slug, or launch without the required validated evidence
- **Proposed resolution**: Define a two-phase allocation contract that allocates and persists the immutable launch identity before evidence materialization, then launches only after the helper writes and validates the sidecar, or change the sidecar contract so its pre-launch fields are distinct from the post-allocation `STEP`



### FINDING_7:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/step-8-ci-fixer.sh:70-93 and <TMPDIR>/plan.txt:26,70
- **Concern**: The plan says valid `FAILED_RUN_ID` and `MAIN_FAILED_RUN_ID` handoff values are authoritative but does not define precedence or rejection when both are present and disagree. Scenario: If the handoff contains two valid numeric IDs for different failures, the wrapper can select an unintended run or construct identity and evidence for the wrong failure; the listed edge case has no specified routing behavior
- **Proposed resolution**: Specify the accepted relationship between the two fields, including which field applies to PR versus main-branch failures, and fail closed on an unexplained disagreement before tier selection or evidence collection



### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/ci_fixer_lane.py:168-177
- **Concern**: The planned invariant-primary carve-out does not relax mandatory numeric GitHub run ID validation. `_validated_run_identity` still rejects empty `--run-id`, and `_resolve_run_id` still resolves a failed PR run before the lane can run without CI failure evidence. On a green PR with `NEEDS_USER_REASON=architectural-invariants-violation` and no `FAILED_RUN_ID`, start either bails or binds the wrong run ID, so delegated invariant repair never launches.. Scenario: Add an explicit invariant-primary mode: skip `_resolve_run_id` and PR failed-run lookup; allow a documented sentinel or alternate identity field; require sidecar `RUN_ID` to match the launch envelope without forcing a GitHub Actions run ID when none exists.
- **Proposed resolution**: 



### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: architecture
- **Location**: skills/implement/references/ship-pr-ci-fix.md
- **Concern**: The plan mandates a single sanctioned invariant-evidence materialization helper but lists no implementation deliverable and no body contract for `$IMPLEMENT_TMPDIR/architectural-invariants.md`. Nothing in the repo writes that file today; violation text currently lives in handoff `DETAIL`/`DETAIL_FILE` and `architectural-invariant-note.md`. Without a named helper and content mapping, tests can pass on prose while runtime materialization is undefined.. Scenario: Add a firm `### NEW:` or `### UPDATED:` helper (Python CLI verb or thin wrapper), specify inputs from handoff `DETAIL`/`DETAIL_FILE` and existing invariant note artifacts, and require bounded redacted body bytes plus the `.identity.env` sidecar before wrapper start.
- **Proposed resolution**: 



### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/implement/scripts/step-8-ci-fixer.sh:79-93
- **Concern**: Wrapper start mode does not define how invariant-primary is signaled or how to skip failed-run resolution before tier selection. Current flow resolves `RUN_ID` from `CI_RUN_ID`, stale status, or `ci_monitor.resolve_failed_run_id_once` whenever it is empty, which runs even if invariant evidence exists and can select an unrelated failed run on a green PR.. Scenario: Require start mode to read handoff `NEEDS_USER_REASON` or an explicit `--invariant-primary` flag, skip lines 79-93 on that path, and only then materialize or consume canonical invariant evidence.
- **Proposed resolution**: 



### FINDING_11:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/ci_fixer_lane.py:474-492
- **Concern**: After skipping `_collect_evidence` for invariant-primary, the plan does not define the `EvidenceState` used by `_dispatch` and `_persist`. `main()` always collects CI logs today; `_dispatch` always passes `evidence.path` as `--failure-log`. Invariant-only launches would still require a distilled/raw CI log or fail closed with no usable evidence.. Scenario: Branch invariant-primary before evidence collection: build `EvidenceState` from validated `architectural-invariants.md` (distinct `EVIDENCE_KIND`), pass it to `_dispatch`, and allow the CI launcher to run with invariant evidence alone when no failure log exists.
- **Proposed resolution**: 



### FINDING_12:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/implement/references/ship-pr-ci-fix.md:36-44
- **Concern**: Prior invariant-evidence fix remains incomplete because evidence must be materialized before start but must contain the TIER, ATTEMPT, and dynamic STEP that start selects; the canonical RUN_ID for a no-failed-run invocation is also undefined. Scenario: The helper cannot construct the required identity without duplicating wrapper selection, while the wrapper cannot start until the evidence exists; invariant-primary recovery can fail or produce identities that the lane rejects
- **Proposed resolution**: Move evidence materialization into wrapper start after identity selection, define the canonical invariant-only RUN_ID, and atomically write and validate the evidence plus sidecar before launching the lane



### FINDING_13:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/implement/scripts/step-8-ci-fixer.sh:66-72
- **Concern**: Prior failed-run handoff fix remains incomplete because precedence or rejection is undefined when FAILED_RUN_ID and MAIN_FAILED_RUN_ID are both valid but disagree. Scenario: The wrapper may launch against the wrong PR or default-branch run, so the fixer receives unrelated evidence and repairs the wrong failure
- **Proposed resolution**: Define route-aware precedence, or fail closed on disagreement, and cover the valid-but-different case in the planned authoritative-handoff fixture



### FINDING_14:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/step-8-ci-fixer.sh:68-72
- **Concern**: The plan does not define how retry-next-tool preserves waterfall progress when the prior fixer changed HEAD. Scenario: The current rounds identity is bound to STARTING_HEAD and INPUT_FINGERPRINT; a fresh start after HEAD changes can reject prior rounds as foreign or restart at the first tier instead of selecting the next tool
- **Proposed resolution**: Persist a waterfall lineage and attempted-tier set separately from each tier's immutable launch identity, then make the planned multi-tier fixture return retry-next-tool after changing HEAD and verify that the next tier starts exactly once



### FINDING_15:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: architecture
- **Location**: skills/implement/references/ship-pr-ci-fix.md
- **Concern**: The plan requires a sanctioned invariant-evidence materialization helper but names no firm implementation file. Scenario: The cutover calls a helper before each invariant-tier start to write `$IMPLEMENT_TMPDIR/architectural-invariants.md` and `$IMPLEMENT_TMPDIR/architectural-invariants.md.identity.env`. No `### NEW:` / `### UPDATED:` module, script, or CLI verb owns that writer. Nothing in the repo writes those paths today. The invariant-primary branch is not implementable as specified.
- **Proposed resolution**: Add one firm helper surface (for example a `python/cli.py` verb or thin wrapper script), list it under Files to modify/create, and wire ship-pr-ci-fix.md to invoke it with explicit inputs from `NEEDS_USER_REASON` / `DETAIL` / `DETAIL_FILE` and the launch identity fields.



### FINDING_16:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/ci_fixer_lane.py
- **Concern**: Invariant-primary mode has no explicit wire contract on the wrapper or lane. Scenario: The plan requires skipping failed-run resolution and CI-log collection only for architectural-invariant-primary invocations, while ordinary CI failures keep current behavior. Today `--invariant-evidence` is optional and `main()` always runs `_resolve_run_id()` and `_collect_evidence()`. The wrapper also forwards evidence whenever `architectural-invariants.md` exists. Without an explicit primary flag/handoff token, a stale evidence file can suppress CI collection or a green-PR violation can still require a numeric failed run.
- **Proposed resolution**: Add an explicit invariant-primary signal (`--invariant-primary` or equivalent) on wrapper start and `ci fixer-lane`, branch lane entry to skip run-id resolution and `_collect_evidence` only on that path, and forbid forwarding optional invariant evidence on ordinary CI-failure tiers.



### FINDING_17:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/implement/scripts/step-8-ci-fixer.sh:79-93
- **Concern**: Prior FINDING_1 fix is incomplete: numeric CI run-id requirements still block green-PR invariant violations. Scenario: The plan orders the invariant branch first and allows proceeding without `FAILED_RUN_ID`, but the wrapper still resolves a numeric GitHub run ID before start and fails on `unresolved-run-id`, and the lane rejects non-digit `run_id`. A compose-time `architectural-invariants-violation` on green PR checks has no failed run to bind. The delegated repair path still bails before tier start.
- **Proposed resolution**: Define invariant-primary run identity explicitly (for example bind sidecar `RUN_ID` to `LARCH_RUN_ID` and relax numeric-only validation on that path only), skip PR run-id resolution in wrapper start mode, and add harness coverage for violation-without-`FAILED_RUN_ID`.



### FINDING_18:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/implement/scripts/step-8-ci-fixer.sh
- **Concern**: The plan reads `MAIN_FAILED_RUN_ID` from the wrong handoff surface. Scenario: Approach item 7 and the wrapper update require reading `MAIN_FAILED_RUN_ID` from `.ship-route-exit-handoff.env`. `dispatch_ship._write_ship_route_handoff()` only writes `FAILED_RUN_ID` from payload `failed_run_id`; `MAIN_FAILED_RUN_ID` is materialized in `$IMPLEMENT_TMPDIR/main-health.env` during preflight/main-health. Default-branch failures that differ from the PR run will not reach the authoritative main run ID the plan intends.
- **Proposed resolution**: Specify and implement the real source of truth: read `MAIN_FAILED_RUN_ID` from `main-health.env` (or teach ship route-exit to copy it into the handoff), document precedence when both PR and main run IDs exist, and add a fixture for distinct PR vs main run IDs.



### FINDING_19:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/implement/references/ship-pr-ci-fix.md:37-41
- **Concern**: The prior invariant-sidecar fix remains incomplete because evidence must bind `TIER`, `ATTEMPT`, and dynamic `STEP` before the wrapper start that selects and emits those values. The plan also does not define the non-CI `RUN_ID` source or the source content for `architectural-invariants.md`.. Scenario: On a green PR with no failed CI run, the prompt cannot construct the required sidecar before start without duplicating wrapper tier selection and step derivation. The lane may therefore receive no evidence, mismatched identity, or an undefined run identity and fail before delegated repair.
- **Proposed resolution**: Make wrapper start own invariant preparation after it selects the tier, attempt, step, and explicit invariant-mode run identity. Define the stable `RUN_ID` source and require the wrapper or a prepare subcommand to materialize the evidence atomically from the validated handoff `DETAIL` or `DETAIL_FILE` and durable invariant note before launching the lane.



### FINDING_20:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/implement/scripts/step-8-ci-fixer.sh:70-71
- **Concern**: The prior failed-run handoff fix remains incomplete because the plan requires reading both `FAILED_RUN_ID` and `MAIN_FAILED_RUN_ID` but does not define precedence or rejection when both valid numeric values disagree.. Scenario: A default-branch failure can have a run ID distinct from the PR run. An implementation that takes the first valid field may launch the fixer against the wrong run, despite the plan listing disagreement as an edge case and requiring stale run IDs to be rejected.
- **Proposed resolution**: Define route-specific run-ID selection using the handoff reason or an authoritative field. Fail closed on an unexplained disagreement, and add the disagreement case to the mandated handoff integration coverage.



