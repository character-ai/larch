### FINDING_1: Harden all review-snapshot creation paths, including post-coder artifacts
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-dyn-Artifact Boundary Auditor
- **Severity**: major
- **Concern**: Review snapshots are not consistently created through safe, exclusive, no-follow writes. The predictable pre-coder snapshot root remains vulnerable to planted symlinked ancestors, cleanup-time inventory writes bypass hardening, and `post-coder-head.txt` is written separately through bare `_write_text`. This leaves snapshot creation and later staging exposed to same-UID path substitution or stale artifact use.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add post-coder-head.txt to the hardened snapshot contract: safe random exclusive no-follow write plus post-write validation, either in snapshot.py or via ### UPDATED: python/larch/review/round_runner.py, and validate the file before _round_diff_base and _collect_round_stage_paths use it
  - From Cursor-Innovation: Harden directory creation in snapshot.py: reject symlinked ancestors on the resolved root, create the leaf with exclusive semantics, and revalidate the resolved root is a regular directory before writing artifacts
  - From Cursor-Innovation: Preserve the current chmod 0444 pass (and _harden_pre_coder_snapshot_perms) immediately after each trusted atomic replacement, and note the behavior in the SECURITY.md update
  - From Cursor-Innovation: Include this cleanup-time inventory write in the snapshot safe atomic write helper and post-write revalidation before cleanup proceeds
  - From Cursor-dyn-Artifact Boundary Auditor: Extend snapshot.py staging validation to cover round_dir/post-coder-head.txt (containment, regular-file/no-follow read, HEAD consistency) or list round_runner.py/review_and_fix.py in Files to modify/create for safe atomic creation


### FINDING_2: Route every direct snapshot consumer through trusted validation
- **Reviewer(s)**: Cursor-Innovation, Codex-dyn-Artifact Boundary Auditor
- **Severity**: major
- **Concern**: `coder_runner.py` and `review_and_fix.py` still read snapshot files directly before the hardened snapshot validation path runs. Symlinked, incomplete, stale, or tampered artifacts can therefore influence stale-HEAD gating, stage-path collection, LOC escalation, delta comparison, or failed-coder cleanup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add ### UPDATED: python/larch/review/coder_runner.py and ### UPDATED: python/larch/review/review_and_fix.py (or export one trusted snapshot loader from snapshot.py and replace every direct pre-coder/self-review read in those modules)
  - From Codex-dyn-Artifact Boundary Auditor: Update every direct snapshot consumer, including coder_runner.py and review_and_fix.py, to call one validating snapshot load before mode detection, staging, delta comparison, or cleanup, and abort on any present-but-invalid artifact set


### FINDING_3: Require complete snapshot validation before selecting cleanup mode
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Concern**: `_snapshot_mode` can classify a tracked-only or incomplete snapshot directory as `full` before the complete artifact set and patch inventory are validated. A partial or interrupted snapshot can consequently enter full cleanup or staging paths with incomplete data.
- **Suggested revisions (informational for voters; coder decides)**:


### FINDING_4: Fail loudly on invalid coverage artifacts in final reports
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Cursor-dyn-Artifact Boundary Auditor
- **Severity**: major
- **Concern**: The final-report consumer currently maps all `load_coverage` failures to an empty summary. Once coverage loading rejects partial, unsafe, or inconsistent artifacts, `_plan_coverage_summary_line` must distinguish genuine absence from invalid presence and fail closed rather than silently suppressing corruption or aborting through an uncaught exception.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add ### UPDATED: python/larch/report/final_report.py to surface an explicit error marker when load_coverage rejects a partial or unsafe set, or define load_coverage to raise and handle that at the step-16/17 compose boundary
  - From Codex-Innovation: Add `python/larch/report/final_report.py` to the firm changes. Use a strict coverage-load result or explicit invalid-artifact exception so genuine absence remains the legacy no-coverage case while unsafe or partial artifacts abort final-report generation.
  - From Cursor-Pragmatic: Add ### UPDATED: python/larch/report/final_report.py and call the hardened loader/validator with fail-closed behavior (empty plan-coverage line or bounded error text) when artifacts are present but untrusted
  - From Cursor-dyn-Artifact Boundary Auditor: Add ### UPDATED: python/larch/report/final_report.py to call the hardened validated loader and surface ShipError or an explicit error summary line; keep wholly absent legacy coverage as empty output


### FINDING_5: Distinguish absent, invalid, and unsafe coverage across all consumers
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Codex-dyn-Artifact Boundary Auditor
- **Severity**: major
- **Concern**: The read-side contract for coverage artifacts is underspecified. Partial, malformed, symlinked, stale, or internally inconsistent coverage can still collapse into `None` or a default `closes` result, allowing final reports, deferred inventories, PR/link rendering, or finalization to proceed as if coverage were wholly absent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Pin the contract in scope_disposition.py: None only for wholly absent legacy sets; partial or unsafe sets raise ShipError (or return a dedicated error object) and never flow through to PR link kind, deferred inventory, or final-report prose
  - From Cursor-Pragmatic: Make wholly absent return None; make partial/unsafe raise a dedicated error or return an explicit invalid status; update disposition_link_kind, disposition_deferred_inventory, and final_report to treat invalid as fail-closed per the edge-case that forbids silent empty summaries
  - From Codex-dyn-Artifact Boundary Auditor: Make every consumer distinguish wholly absent legacy artifacts from present-invalid artifacts and propagate the existing failure result or ShipError before rendering, PR routing, finalization, staging, or cleanup can act


### FINDING_6: Preserve invalid scope-disposition state instead of defaulting to closes
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Concern**: Malformed, unsafe, fingerprint-invalid, or incomplete `scope-disposition.json` is currently treated like an absent artifact. Consumers can therefore default to `closes` and continue deferred-inventory or final-report processing instead of failing closed on a corrupted or tampered disposition.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Distinguish absent from invalid disposition artifacts and propagate invalid status to every consumer. Reject unsafe, malformed, incomplete, or coverage-mismatched records before selecting part-of versus closes, rendering inventory, or producing the final report.


### FINDING_7: Require live repository validation for every coverage consumer
- **Reviewer(s)**: Cursor-Pragmatic, Codex-Requirements
- **Severity**: major
- **Concern**: Structural validation alone remains possible when consumers omit `repo_root`. Legacy readers and finalization paths can accept stale but internally consistent artifacts whose HEAD, plan, manifest, baseline, or working-tree diff changed after creation. Callers must supply or derive the repository root, with an explicit fail-closed behavior when live validation is unavailable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: In scope_disposition.py route those helpers through one validated load API that attempts repo_root recompute when git top-level resolves, and fail closed on mismatch; document the intentional structural-only fallback when repo_root truly unavailable
  - From Codex-Requirements: Require live recomputation for every coverage consumer. Update callers such as `python/larch/report/final_report.py`, `python/larch/git/pr_body.py`, and `python/larch/state/finalize.py` to supply or derive the repository root, and fail closed when live inputs cannot be validated.


### FINDING_8: Do not require scope disposition for valid coverage-only flows
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Concern**: Treating `scope-disposition.json` as mandatory in the coverage artifact set would reject valid advisory and middle flows where coverage is published before any disposition exists or no disposition is needed. Coverage-set validation and disposition validation must remain separate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Define the complete coverage set as JSON, env, untouched-path, and todo files. Validate disposition separately when present or required, including its coverage fingerprint.


### FINDING_10: Validate manifest and baseline inputs as trusted artifacts
- **Reviewer(s)**: Codex-dyn-Artifact Boundary Auditor
- **Severity**: major
- **Concern**: Coverage creation and recomputation accept manifest and `step2-baseline.txt` through ordinary `is_file`/`read_text` paths. Symlinked or replaced inputs can redirect reads or alter the covered fingerprint between validation and use, producing internally consistent but attacker-controlled coverage that affects shipping and PR routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-Artifact Boundary Auditor: Add trusted no-follow, contained regular-file reads for manifest and baseline inputs, and bind validation to the opened descriptors or revalidate immediately before computing and publishing coverage


### FINDING_1: Harden mav-apply post-coder-head creation
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: major
- **Concern**: `review_and_fix.py` mav-apply mode still creates `post-coder-head.txt` through an unlink followed by bare `_write_text`, bypassing the exclusive no-follow trusted-write contract, final-path revalidation, and permission hardening used by `round_runner.py`. A same-UID symlink or partial replacement can therefore poison the diff base and staging inputs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add review_and_fix.py to the firm write hardening list and route mav-apply post-coder-head creation through the same snapshot trusted-write helper used in round_runner.py, including chmod 0444 hardening.
  - From Cursor-Pragmatic: A same-UID symlink or partial file in the round directory can redirect or poison the mav-apply post-coder head before later trusted validation runs, so diff-base and stage-path collection can diverge from the validated snapshot contract. Add review_and_fix.py to the post-coder-head write hardening step: route mav-apply creation through the same snapshot trusted-write helper used in round_runner.py, with final-path revalidation and permission hardening; extend test_review_and_fix.py to cover the mav-apply writer.


### FINDING_2: Make snapshot validation the sole cleanup mode authority
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: Cleanup paths still re-derive snapshot mode through the legacy `_snapshot_mode` heuristic. Tracked-only directories can be classified as full before patch inventory validation, allowing validated snapshots with incomplete patch data to enter full cleanup and stale-HEAD handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Make the complete validator the sole mode authority: replace _snapshot_mode classification with validator output and pass the validated mode into cleanup/restoration (or have cleanup call only validator-backed APIs). Update coder_runner stale-HEAD gating to use the same validated snapshot contract.


### FINDING_3: Require live validation before recording disposition
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: major
- **Concern**: `record_disposition` and its CLI action can load or fingerprint persisted coverage without `repo_root` or live recomputation. Stale, partial, symlinked, unsafe, or mismatched coverage can therefore be frozen into `scope-disposition.json` before downstream consumers validate it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add repo_root (or a pre-validated live coverage object) to record_disposition, recompute/validate coverage before persisting disposition, and fail closed when artifacts are partial, unsafe, or live-mismatched.
  - From Cursor-Innovation: Add repo_root to record_disposition (and its CLI action), load coverage only through the hardened live-validating API, and fail closed when recompute or containment checks fail


### FINDING_4: Remove unvalidated disposition wrapper reads
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Codex-Innovation
- **Severity**: major
- **Concern**: `disposition_link_kind` and `disposition_deferred_inventory` still permit legacy or repeated raw reads without a validated `repo_root` and live artifact check. PR-body and finalization paths can consequently treat invalid disposition as `closes`, empty inventory, or otherwise render data that was replaced after an earlier validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Make the trusted loaders the only read path inside these helpers (require repo_root or fail closed), raise on invalid present artifacts, and keep absent-only None semantics for optional flows.
  - From Codex-Arch: Change the wrapper APIs to require or derive a validated repository root, route them through the live-validating coverage/disposition loader, and update all callers to propagate failure instead of defaulting to empty inventory or `closes`.
  - From Codex-Innovation: Return the validated coverage/disposition result from the hardened validation call and pass it through rendering and finalization, or require these helpers to receive repo_root and perform the same trusted live validation themselves.


### FINDING_5: Harden scope-disposition artifact writes
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: `record_disposition` publishes `scope-disposition.json` through default atomic writing to a predictable destination. A same-UID symlink at that path can redirect the write outside `tmpdir`, while later readers may treat the invalid artifact as absent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Extend the plan's trusted-write contract to disposition artifacts: random exclusive no-follow temp creation, final-path revalidation, and safe temp cleanup for record_disposition and any other scope-disposition writers


### FINDING_6: Fail closed on invalid disposition in final-report summaries
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: `_plan_coverage_summary_line` can still receive `None` from `load_disposition` for malformed, symlinked, or fingerprint-invalid `scope-disposition.json`, causing final reports to render `disposition: none` and mask corruption.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Apply the same three-state disposition contract in final_report: wholly absent stays none, valid-present renders as today, invalid-present raises ShipError or returns an explicit bounded failure instead of masking corruption


### FINDING_7: Validate disposition before finalize teardown gating
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: Finalize teardown selects the done-rename branch through `disposition_link_kind` before resolving `repo_root`. This ordering can leave the partial-disposition gate on legacy unvalidated loading rather than the required live-validation contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Reorder finalize teardown (or add an explicit pre-check): resolve repo_root first, run trusted disposition validation, then decide whether proceed-partial suppresses the done rename


### FINDING_8:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/review/snapshot.py:672-691
- **Concern**: [SCOPE-REDUCTION] Preserve safe reuse of an existing snapshot root instead of requiring every root creation to be exclusive. Scenario: `_write_pre_coder_snapshot` currently clears and rewrites the deterministic per-round directory. After an interrupted attempt leaves a valid directory, literal exclusive root creation makes the next attempt fail before it can replace stale or partial artifacts, breaking existing recovery and requiring manual cleanup.
- **Proposed resolution**: Create the directory exclusively only when absent. When it already exists, validate the directory and every ancestor without following symlinks, then safely clear and republish the snapshot artifacts.


