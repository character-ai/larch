### [Plan Review] FINDING_2

### FINDING_2: Compose precheck bypasses unified consumption and advancement
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: major
- **Concern**: `_compose_precheck_result` and `_invariant_compose_precheck_result` still call `note_consumable` / `invariant_note_consumable` without `repo_root` or `base_ref`, then apply a separate fingerprint-stale gate (or return `status=current` when `root is None`). After the plan removes HEAD-match-only consumability and requires live identity validation plus advancement on drift, this split path cannot advance coverage or return `status=current` during compose when a safe docs-only or log-only commit landed, breaking once-per-run compose reuse.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Refactor both precheck helpers to pass resolved `repo_root` and `BASE_REF` into the consumption helpers, rely on the unified consumable result only, and delete the redundant parallel fingerprint-stale branch. Add compose-precheck tests that prove safe HEAD drift returns `status=current` without rematerialization.
  - From Cursor-Pragmatic: Pass `repo_root=root` and the resolved `base_ref` into consumable checks, delete the `root is None → current` branch, and rely on the shared advancement plus covered-fingerprint validation inside consumable before returning `status=current`.


### [Plan Review] FINDING_4

### FINDING_4: Unavailable-note identity rules conflict with universal consumption requirements
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Concern**: The plan permits unavailable notes without fingerprints, but requires every consumed note to have a non-empty covered identity. The ship loader checks consumability before reading `NOTE_STATE`, so such an unavailable note cannot reach unavailable outcome classification and instead repeatedly requests reassessment or emits the existing materialization-failed result.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Define a state-specific terminal path for unavailable artifacts that emits the unavailable outcome without claiming reusable coverage, or require every unavailable note intended for normal consumption to carry a validated covered identity. Add the corresponding loader behavior to the firm plan.

---

**Merge notes (diagnostic only):**
- FINDING_1 subsumed Cursor-Arch #1 plus Cursor-Pragmatic #5 and #6 (same advancement subsystem; distinct verbatim fixes preserved).
- FINDING_2 subsumed Cursor-Arch #2 and Cursor-Pragmatic #4 (same compose-precheck bypass).
- FINDING_3 and FINDING_4 kept separate (ship gate clobber vs unavailable-note consumption identity).
- All three inventory slots appear; no `[OUT_OF_SCOPE]` blocks; no empty-merge attestation.

