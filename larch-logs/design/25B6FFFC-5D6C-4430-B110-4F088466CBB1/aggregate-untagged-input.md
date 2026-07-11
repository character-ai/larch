### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/review/review_and_fix.py:932-939
- **Concern**: Harden mav-apply post-coder-head creation (FINDING_1 incomplete). Scenario: The plan hardens post-coder-head writes only in round_runner.py. review_and_fix.py mav-apply still creates post-coder-head.txt via bare _write_text after unlink, bypassing exclusive no-follow atomic publish and final-path revalidation. Staging and _round_diff_base can trust a symlinked or replaced head artifact.
- **Proposed resolution**: Add review_and_fix.py to the firm write hardening list and route mav-apply post-coder-head creation through the same snapshot trusted-write helper used in round_runner.py, including chmod 0444 hardening.

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/review/snapshot.py:98-104
- **Concern**: Retire legacy _snapshot_mode heuristic inside cleanup paths (FINDING_3 incomplete). Scenario: The plan adds a complete snapshot validator but still routes cleanup through _snapshot_mode, which classifies tracked-only directories as full before patch inventory validation. coder_runner.py and _cleanup_failed_coder_attempt re-derive mode from that helper after entry, so validated snapshots can still enter full cleanup with incomplete patch data.
- **Proposed resolution**: Make the complete validator the sole mode authority: replace _snapshot_mode classification with validator output and pass the validated mode into cleanup/restoration (or have cleanup call only validator-backed APIs). Update coder_runner stale-HEAD gating to use the same validated snapshot contract.

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/scope_disposition.py:782-824
- **Concern**: Require live validation in record_disposition and the record CLI action. Scenario: The plan mandates live repo_root validation for every coverage consumer but does not name record_disposition. Its default path and scope-disposition record CLI call load_coverage(tmpdir) without repo_root or live recompute, so a symlinked, partial, or stale four-file set can be frozen into scope-disposition.json.
- **Proposed resolution**: Add repo_root (or a pre-validated live coverage object) to record_disposition, recompute/validate coverage before persisting disposition, and fail closed when artifacts are partial, unsafe, or live-mismatched.

### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/implement/scope_disposition.py:598-611
- **Concern**: Refactor disposition_link_kind and disposition_deferred_inventory to the three-state contract. Scenario: These helpers still call legacy load_coverage/load_disposition that map invalid present artifacts to None. pr.py, pr_body.py, and finalize.py depend on them; invalid disposition can still render as closes or empty inventory even after sibling files adopt hardened loaders.
- **Proposed resolution**: Make the trusted loaders the only read path inside these helpers (require repo_root or fail closed), raise on invalid present artifacts, and keep absent-only None semantics for optional flows.

### FINDING_5:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/scope_disposition.py:598-618; python/larch/git/pr_body.py:417-426; python/larch/state/finalize.py:701
- **Concern**: Re-raise accepted prior finding: no-repository wrapper consumers remain outside the live-validation contract. Scenario: The plan requires every coverage consumer to perform live recomputation, but `disposition_link_kind()` and `disposition_deferred_inventory()` still have no `repo_root` parameter, and their PR-body and finalization callers invoke them without one. These paths can therefore continue to load persisted artifacts structurally or default invalid disposition state to `closes`, bypassing the required live validation.
- **Proposed resolution**: Change the wrapper APIs to require or derive a validated repository root, route them through the live-validating coverage/disposition loader, and update all callers to propagate failure instead of defaulting to empty inventory or `closes`.

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: security
- **Location**: python/larch/implement/scope_disposition.py:823
- **Concern**: Harden scope-disposition.json writes, not only the four coverage files. Scenario: record_disposition still publishes scope-disposition.json through default atomic_write on a fixed destination path; a same-UID symlink planted at scope-disposition.json can redirect the write outside tmpdir while reads later treat invalid presence like absence
- **Proposed resolution**: Extend the plan's trusted-write contract to disposition artifacts: random exclusive no-follow temp creation, final-path revalidation, and safe temp cleanup for record_disposition and any other scope-disposition writers

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/scope_disposition.py:791
- **Concern**: Require live trusted coverage before recording disposition. Scenario: record_disposition binds fingerprints from coverage or load_coverage(tmpdir) with no repo_root or live recompute, so stale or symlinked persisted coverage can be frozen into scope-disposition.json before ship, PR, or finalize consumers run
- **Proposed resolution**: Add repo_root to record_disposition (and its CLI action), load coverage only through the hardened live-validating API, and fail closed when recompute or containment checks fail

### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/report/final_report.py:527-532
- **Concern**: Fail closed on invalid-present disposition in final-report coverage summary. Scenario: _plan_coverage_summary_line hardens only coverage loading in the plan text, but it still calls load_disposition, which maps malformed, symlinked, or fingerprint-invalid scope-disposition.json to None and renders disposition: none
- **Proposed resolution**: Apply the same three-state disposition contract in final_report: wholly absent stays none, valid-present renders as today, invalid-present raises ShipError or returns an explicit bounded failure instead of masking corruption

### FINDING_9:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/state/finalize.py:698-701
- **Concern**: Resolve repo_root before the partial-disposition rename gate. Scenario: finalize teardown chooses the done rename branch via disposition_link_kind before any repo_root resolution; the hardened live-validation APIs the plan requires need repo_root, so implementers may leave this path on legacy load_disposition semantics
- **Proposed resolution**: Reorder finalize teardown (or add an explicit pre-check): resolve repo_root first, run trusted disposition validation, then decide whether proceed-partial suppresses the done rename

### FINDING_10:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: security
- **Location**: python/larch/implement/scope_disposition.py:598-612
- **Concern**: Disposition rendering helpers still permit a raw second read after validation. Scenario: PR and finalization paths can validate a disposition, then call disposition_link_kind or disposition_deferred_inventory, which reloads the artifact without repo_root or live validation. A same-UID replacement between those operations can make invalid data default to closes or suppress deferred inventory, bypassing the fail-closed contract.
- **Proposed resolution**: Return the validated coverage/disposition result from the hardened validation call and pass it through rendering and finalization, or require these helpers to receive repo_root and perform the same trusted live validation themselves.

### FINDING_11:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/review/review_and_fix.py:934-938
- **Concern**: Harden mav-apply post-coder-head creation, not only round_runner. Scenario: The plan routes post-coder-head.txt creation through snapshot trusted-write only in round_runner.py. review_and_fix.py mav-apply mode still unlinks and writes post-coder-head.txt with bare _write_text plus chmod, leaving accepted FINDING_1 incomplete. That path feeds _round_diff_base and staging without the exclusive no-follow publish contract.
- **Proposed resolution**: A same-UID symlink or partial file in the round directory can redirect or poison the mav-apply post-coder head before later trusted validation runs, so diff-base and stage-path collection can diverge from the validated snapshot contract. Add review_and_fix.py to the post-coder-head write hardening step: route mav-apply creation through the same snapshot trusted-write helper used in round_runner.py, with final-path revalidation and permission hardening; extend test_review_and_fix.py to cover the mav-apply writer.
