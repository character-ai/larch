## Decision 1: Atomic write hardening scope
- **Question**: Which state writers need hardening?
- **Resolution**: Only `run_logs.py:_atomic_write` and `tokens.py:_atomic_text`. Other callers (clarify, rendering, plan_review, etc.) are not mentioned in the issue.
- **Source**: codebase + issue text

## Decision 2: Exact hardening params for run_logs and tokens
- **Question**: Add `nofollow=True` only, or also switch to fixed-temp + `exclusive=True`?
- **Resolution**: Add `nofollow=True` to both callers. Both use `prefix=` (random temp), so `exclusive=True` has no effect; no need to switch temp strategy. `mode=0o600` not appropriate for manifest/ledger files (already in tempdir-scoped directories).
- **Source**: codebase (larch_io.py logic showing fixed_temp gate)

## Decision 3: rmtree+replace locations in scope
- **Question**: Both rmtree+replace occurrences (lines 1808, 2174)?
- **Resolution**: Yes, both. Issue says "no rmtree-before-rename" without exception.
- **Source**: issue text

## Decision 4: suppress(Exception) locations in scope
- **Question**: Which of the 8 suppress(Exception) calls in run_logs.py are in scope?
- **Resolution**: Only the three around commit/manifest IO: line 1874 (manifest update in _commit_run), line 1884 (breadcrumbs in _commit_run), and line 2207 (full flush). Lines 733–746 (best-effort report writes) and 1147 (vendor diagnostics script) remain as-is.
- **Source**: issue text ("commit/manifest IO"), codebase inspection

## Decision 5: Don't-touch boundaries
- **Question**: What must not change?
- **Resolution**: symlink-escape guard at run_logs.py:1550/1692; BaseException seam in review_and_fix.py; suppress(Exception) in research.py, ship.py, agents.py, etc.
- **Source**: issue text (explicit don't-touch section)
