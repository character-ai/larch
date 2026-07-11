## Proposed Design Outline

### Goals
- Treat plan-coverage artifacts and review snapshots as trusted, validated artifacts across their full lifecycle (creation + consumption).
- Reject missing, symlinked, stale, mismatched, non-regular, or out-of-root coverage/snapshot files on every read path.
- Create temporary coverage/snapshot files with unpredictable, exclusive, no-follow semantics; revalidate containment and file type before use or replacement.

### Non-goals
- No change to coverage *semantics* (touched/untouched sets, band thresholds, disposition gate) or to what the git-tree snapshots capture.
- No change to `larch_io.atomic_write` shared-helper defaults (high blast radius); hardening is opt-in per call site.
- No redesign of artifact file formats and no new public CLI verbs beyond what hardening requires.

### Approach sketch
- Add a small shared "trusted artifact" check (regular file, not a symlink, within the expected root) reused by both systems.
- `scope_disposition.py`: thread an optional `repo_root` into load paths where the caller has it; recompute coverage and compare the covered fingerprint, rejecting stale/mismatched; harden `write_coverage` temp creation via `atomic_write` safe flags; reject bad files on read.
- `snapshot.py`: stop using bare `write_text` for `.patch`/`.txt` files in the shared predictable `/tmp/larch-pre-coder-snapshots/` dir — use safe temp creation (mkstemp + no-follow + exclusive) or a private per-session dir; validate regular-file + containment on read alongside the existing HEAD-equality gate.
- Fail loudly and closed (G-Py-4); re-verify after integrity-critical writes (G-Py-8).

### Surfaces in scope
- `python/larch/implement/scope_disposition.py`
- `python/larch/review/snapshot.py` (and `python/larch/review/_raf_util.py` read/write helpers as needed)
- `python/larch/io.py` (reuse existing `atomic_write` safe flags; no default change)
- Consumers without `repo_root`: `python/larch/report/final_report.py`, `python/larch/git/pr.py`, `python/larch/git/pr_body.py`, `python/larch/state/finalize.py`, `python/larch/implement/dispatch_commit_route.py`
- Tests under `python/tests/implement/` and `python/tests/review/` (plus existing scope-disposition/snapshot coverage)

### Open questions
- Relocate `pre_coder_snapshot_dir` out of shared `/tmp` into a private per-session dir (stronger isolation) vs. keep `/tmp` and rely on safe exclusive/no-follow writes (smaller diff). To be resolved in plan drafting (Step 2b).
