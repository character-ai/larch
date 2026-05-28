### FINDING_1: Blanket validator breaks empty step3 tmpdir contract
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: important
- **Concern**: The planned post-argv design tmpdir validator would reject an empty `--design-tmpdir`, conflicting with existing step3/gatec behavior that exits 0 with a warning when the tmpdir is intentionally empty.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: test-emit-design-plan-preview fails under make lint; Step 3 preview behavior regresses Skip validation when variant=step3 and design_tmpdir is empty (preserve exit 0), or move validation after the step3 friendly branch and document the exception in emit-design-plan-preview.md
  - From Cursor-Innovation: Skip validation when design_tmpdir is empty and keep the existing soft-fail branches; or document an explicit exemption and update test-emit-design-plan-preview.sh plus emit-design-plan-preview.md

### FINDING_2: Allowlist paths do not match canonical session roots
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: important
- **Concern**: The validator compares physically resolved candidate paths against raw or incomplete allow prefixes, so valid XDG cache, `/tmp`, or `$TMPDIR` session directories can be rejected, especially on macOS where paths resolve through `/private`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Build default prefixes from ${XDG_CACHE_HOME:-${HOME:-/tmp}/.cache}/larch/sessions plus TMPDIR and /tmp, then canonicalize allowed prefixes with the same physical-path logic before comparison.
  - From Codex-Innovation: Canonicalize and slash-normalize each allow prefix before case comparison
  - From Cursor-Pragmatic: Canonicalize allow-prefix entries with the same physical resolution before comparison, including /tmp and TMPDIR, then normalize trailing slashes
  - From Codex-Pragmatic: Canonicalize allow-prefix entries with the same physical resolution before comparison, including /tmp and TMPDIR, then normalize trailing slashes

### FINDING_3: Validator creates untrusted parent before allowlist check
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: The planned validator creates the candidate parent directory before proving the path is under an allowed root, so rejected inputs can still leave directories outside the intended confinement area.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Do not mkdir untrusted parents before validation. Canonicalize the nearest existing ancestor, append unresolved components for comparison, and only create the parent after the resolved path is proven under an allowed prefix.
  - From Codex-Innovation: Resolve the nearest existing ancestor without mkdir, compare against canonical allowed prefixes, and let callers create the directory only after validation succeeds
  - From Cursor-Requirements: Resolve the nearest existing ancestor without mkdir, compare against canonical allowed prefixes, and let callers create the directory only after validation succeeds
  - From Codex-Requirements: Resolve the nearest existing ancestor without mkdir, compare against canonical allowed prefixes, and let callers create the directory only after validation succeeds

### FINDING_4: Leaf symlink can escape allowed tmp roots
- **Reviewer(s)**: Cursor-Edge, Codex-Edge, Cursor-Pragmatic, Codex-Pragmatic, Cursor-dyn-allowlist-logic, Codex-dyn-allowlist-logic
- **Severity**: important
- **Concern**: Parent-only canonicalization can approve a path whose final component is a symlink to a disallowed location, causing later writes to follow the symlink outside the approved tmp roots.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Reject a symlink final component or canonicalize an existing final directory and re-check that resolved leaf against the allowlist; add a final-symlink regression case
  - From Codex-Edge: Reject a symlink final component or canonicalize an existing final directory and re-check that resolved leaf against the allowlist; add a final-symlink regression case
  - From Cursor-Pragmatic: When the leaf exists, resolve it with cd "$candidate" && pwd -P or reject symlink leaves, then compare that resolved leaf path against the allowlist; add a leaf-symlink regression case
  - From Codex-Pragmatic: When the leaf exists, resolve it with cd "$candidate" && pwd -P or reject symlink leaves, then compare that resolved leaf path against the allowlist; add a leaf-symlink regression case
  - From Cursor-dyn-allowlist-logic: Either reject an existing leaf symlink or follow the leaf when it exists, matching the existing final-component symlink pattern in `skills/design/scripts/revise-plan-with-waterfall.sh:67-83`; add the leaf-symlink escape case to `scripts/test-lib-design-tmpdir.sh`.
  - From Codex-dyn-allowlist-logic: Either reject an existing leaf symlink or follow the leaf when it exists, matching the existing final-component symlink pattern in `skills/design/scripts/revise-plan-with-waterfall.sh:67-83`; add the leaf-symlink escape case to `scripts/test-lib-design-tmpdir.sh`.

### FINDING_5: Validator failures bypass parseable KV failure contracts
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: Wiring generic validator failures directly into scripts with documented KV-style failure output can make invalid tmpdir paths exit nonzero without expected `PUBLISH_OK`, `LOAD_OK`, or `PAUSE_OK` records.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Route validator failures through each script's existing emit_* failure helper where the script documents expected failures as KV plus exit 0

### FINDING_6: Validator wiring exceeds issue-scoped consumers
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: The plan broadens validator wiring beyond the issue-scoped `tally-plan-review.sh` and `dispatch-plan-voters.sh` consumers, increasing diff size and regression surface without a stated need.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Limit the validator wiring in this pass to tally-plan-review.sh and dispatch-plan-voters.sh, plus their docs/tests; file or defer the broader all-consumer sweep unless the feature description is updated to require it.
  - From Codex-Requirements: Limit the validator wiring in this pass to tally-plan-review.sh and dispatch-plan-voters.sh, plus their docs/tests; file or defer the broader all-consumer sweep unless the feature description is updated to require it.

### FINDING_7: Plan omits required SECURITY.md update
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: The plan changes security-relevant behavior for tmpdir confinement and FD-3 newline injection resistance but does not include the repository-required `SECURITY.md` update or justification.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add a minimal SECURITY.md update covering the new design tmpdir allowlist and emit_kv single-line value contract, or explicitly justify why the security policy does not need a change.
  - From Codex-Requirements: Add a minimal SECURITY.md update covering the new design tmpdir allowlist and emit_kv single-line value contract, or explicitly justify why the security policy does not need a change.

### FINDING_8: Voter coverage rename leaves old API files shipping
- **Reviewer(s)**: Cursor-dyn-rename-propagation, Codex-dyn-rename-propagation
- **Severity**: important
- **Concern**: The plan adds renamed voter coverage files but does not explicitly remove the old source and doc paths, risking both APIs shipping and stale sourcers bypassing the missing-symbol hardening.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-rename-propagation: Add explicit deletion steps for scripts/lib-voter-coverage.sh and scripts/lib-voter-coverage.md, or state that the two REWRITTEN entries must be implemented as git mv operations that remove the old paths
  - From Codex-dyn-rename-propagation: Add explicit deletion steps for scripts/lib-voter-coverage.sh and scripts/lib-voter-coverage.md, or state that the two REWRITTEN entries must be implemented as git mv operations that remove the old paths

### FINDING_9: Allowlist case pattern can treat prefixes as globs
- **Reviewer(s)**: Cursor-dyn-allowlist-logic, Codex-dyn-allowlist-logic
- **Severity**: latent
- **Concern**: The allowlist matcher does not explicitly require quoted literal prefixes, so glob metacharacters in `$TMPDIR` or override prefixes could unintentionally broaden allowed paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-allowlist-logic: Specify the exact matcher: build prefixes as normalized literal strings, then use `case "$resolved" in "$prefix"*)` with only the final `*` unquoted.
  - From Codex-dyn-allowlist-logic: Specify the exact matcher: build prefixes as normalized literal strings, then use `case "$resolved" in "$prefix"*)` with only the final `*` unquoted.

### FINDING_10: Parent canonicalization lacks explicit failure guard
- **Reviewer(s)**: Cursor-dyn-allowlist-logic, Codex-dyn-allowlist-logic
- **Severity**: important
- **Concern**: The plan promises return code 2 on parent permission or resolution failure, but the algorithm does not explicitly guard `cd "$parent" && pwd -P`, so callers using `set -e` may exit without the documented diagnostic or return contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-allowlist-logic: Add the explicit conditional in `larch_design_tmpdir_validate`: if parent resolution fails, emit the permission or resolution error and return 2 before building the resolved path.
  - From Codex-dyn-allowlist-logic: Add the explicit conditional in `larch_design_tmpdir_validate`: if parent resolution fails, emit the permission or resolution error and return 2 before building the resolved path.
