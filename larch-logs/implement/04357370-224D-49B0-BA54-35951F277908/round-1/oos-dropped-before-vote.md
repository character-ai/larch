### OOS_1: [OUT_OF_SCOPE] Semantic reassessment on substantive diff change is plan-deferred
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-artifact-safety
- **Severity**: latent
- **Concern**: Refresh updates diff metadata only and reuses Phase-A assessment prose even when the live diff changed substantively after Step 7a. The plan explicitly defers semantic reassessment to prompt-side Phase A; this is the accepted trade-off for recovering context-only drops (~87%), not an implementation gap. Tests document refresh as intentionally re-fingerprinting without reassessing assessment text.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_2: [OUT_OF_SCOPE] Only one refresh+retry cycle on ship path
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: Only one refresh+retry cycle exists in `ship.py`; if `origin/main` or HEAD moves again between refresh and the second pin, the note still drops. The plan specifies a single retry; a loop or reassessment would be new scope.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_3: [OUT_OF_SCOPE] Empty-string `repo_root` not rejected on refresh path
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: `repo_root=""` is not rejected (`None` only), so `Path("").resolve()` could materialize a diff against the process CWD. Same empty-string handling already existed in `pin_note_from_staged()`; production ship always passes a real `repo_root`.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_4: [OUT_OF_SCOPE] Drift recovery not wired on closeout / pin CLI paths
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: latent
- **Concern**: Drift-recovery logic is only added to `ship.py`; `closeout.py` and the pin CLI still call `pin_note_from_staged()` directly. Those surfaces can still drop the note on the same HEAD-drift mismatch, so the branch does not fully eliminate the regression across all implement-run pinning paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Route those callers through the same refresh-and-retry helper, or factor the retry into the shared pin path.

### OOS_5: [OUT_OF_SCOPE] Staged writes via `_write_text_atomic()` lack symlink guards
- **Reviewer(s)**: dyn-dyn-artifact-safety
- **Severity**: latent
- **Concern**: `write_staged_assessment()` (including the new refresh path) still writes via `_write_text_atomic()`, which does not reject symlinked target or `.tmp` paths the way `_write_design_assessment_atomic()` does. This predates the branch; refresh adds a second Phase-B rewrite using the same helper.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_6: [OUT_OF_SCOPE] No ship-level test for refresh-succeeds then retry-pin-fails
- **Reviewer(s)**: dyn-dyn-artifact-safety
- **Severity**: latent
- **Concern**: Unit tests cover refresh success and refresh returning `False`, but there is no ship-level test for “refresh succeeds, retry pin fails” asserting drop-notice text and artifact state. That gap makes the misattribution path in FINDING_3 easier to regress.
- **Suggested revisions (informational for voters; coder decides)**:
