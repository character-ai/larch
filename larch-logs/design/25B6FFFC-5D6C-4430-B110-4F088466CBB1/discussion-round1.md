# Discussion Round 1 — resolved scope & requirements

Source issue: #6852 — Coverage snapshot validation and temporary-file handling are unsafe.

## Decision 1: Scope — which artifact systems to harden
- **Question**: The issue says "Coverage snapshots" but the unsafe properties it lists map to two distinct artifact systems. Which surface(s)?
- **Resolution**: **Both systems** — (A) `python/larch/implement/scope_disposition.py` plan-coverage artifacts and (B) `python/larch/review/snapshot.py` pre-coder / self-review snapshots.
- **Source**: user

## Decision 2: Consumption done-criteria
- **Question**: For read paths, is the must-have active re-validation or safe-handling-only?
- **Resolution**: **Active re-validation** — read paths that have `repo_root` recompute coverage and reject missing/symlinked/stale/mismatched/non-regular/out-of-repo artifacts; read paths without `repo_root` (final-report, pr_body, pr, state/finalize, dispatch_commit_route) harden file-type + containment checks. Behavior change: previously-passing stale/tampered artifacts now fail loudly.
- **Source**: user

## Hard constraints (from codebase, must not break)
- Preserve coverage **semantics**: what counts as touched/untouched, the band thresholds, and the disposition gate (`validate_disposition_for_ship`) behavior for legitimate runs must not change.
- Preserve the `/review-and-fix` coder-cleanup contract: pre-coder/self-review snapshots must still revert coder deltas cleanly and verify post-cleanup state.
- The `[DESIGNED]`/ship flow, final-report summary line, and PR `partial`/`closes` link kind must keep working on valid artifacts.
- `larch_io.atomic_write` is a shared helper with many callers; changing its **defaults** is out of scope (high blast radius). Hardening is opt-in per call site.

## Non-goals
- Do not relocate or redesign the coverage/snapshot file formats (still JSON + KV + patch files).
- Do not change plan-firm-path extraction or todo-blocking classification logic.
- Do not alter git-tree snapshot *semantics* (what is snapshotted), only how files are created and trusted.
- No new public CLI verbs beyond what hardening requires.
