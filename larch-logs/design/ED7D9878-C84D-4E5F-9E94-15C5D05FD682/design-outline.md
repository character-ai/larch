## Proposed Design Outline

### Goals
- Finish wiring ARCHITECTURAL_INVARIANTS.md so every consumer that reads, presents, persists, or assesses GUIDELINES does the same for INVARIANTS. The reader half already landed via #6469.
- Give the invariant assessment blocking teeth at both /design Gate C and /implement Step 8, with agentic auto-remediation (CI-fix / Gate-B style) and a hard-stop only after remediation is exhausted.
- Keep each file independently optional and fail-closed: present includes, absent omits silently, invalid/symlink/non-regular omits and warns.

### Non-goals
- Populating ARCHITECTURAL_INVARIANTS.md with real I-* entries (its own effort). The blocking path stays dormant until entries exist.
- Feeding both files to the Step 2 coder and reviewers (that is #6469).
- Re-implementing the reader half (read_invariants, parse_invariant_entries, the `architectural-invariants read` verb) already on main.

### Approach sketch
- Mirror the remaining 10 cli verbs under the existing `architectural-invariants` namespace with parallel `*_main` entrypoints, per the #6469 precedent. Extract shared private helpers rather than add a `--kind` flag.
- Mirror the artifact layer: invariant assessment, staged, durable-note, materialized-diff constants, paths, and meta env, parameterized by kind.
- Add a blocking "violation" assessment kind (vs guidelines' aspirational "deviation") routed into agentic fix-and-retry, with a bounded fallback hard-stop.
- Wire /design (Step 1d read fold-in, Step 1d.7 + Gate C present-note, persist-design-assessment) and /implement (Step 8 compose gating, ship route-exit, durable note, PR body + final summary).
- Extend SECURITY.md framing and fluff-analysis coverage; mirror the tests.

### Surfaces in scope
- python/larch/core/architectural_guidelines.py; python/larch/cli.py dispatch table + allowlist.
- python/larch/implement/: ship_guidelines.py, ship.py, dispatch_ship.py, ship_resume.py for blocking + remediation routing.
- skills/design/: SKILL.md, references/design-outline.md, references/approval-gates.md.
- skills/implement/: SKILL.md, references/architectural-guidelines-present.md, references/ship-pr-exit-matrix.md, scripts/step-architectural-guidelines-write-compose.sh.
- SECURITY.md; skills/fluff-analysis/scripts/fluff-analysis.py; mirrored tests under python/tests/.

### Open questions
- Remediation retry bound, and whether the /design-side block reuses the Gate B apply loop or a small dedicated loop. Resolve during plan drafting / review.
