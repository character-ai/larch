## Decision 1: Item 1 (bare dir-only Bash probe) scope
- **Question**: Empirical testing confirms `hook-bg-poll-guard.sh` currently ALLOWS a Bash command whose entire text is just the live marker directory path (no verb/bracket/loop/mutation keyword) — none of the 7 gated deny checks fire. Fix the gap and test, test the current allow behavior, or skip item 1?
- **Resolution**: Fix the gap — extend deny coverage so a truly bare dir-only command also denies — then add the regression test asserting deny.
- **Source**: user

## Decision 2: Item 2 (assert_deny STEP verification) scope
- **Question**: `scripts/test-hook-bg-poll-guard.sh` has roughly 80 `assert_deny` call sites; the STEP value written by the preceding `write_marker`/`write_marker_at` call varies per block. Thread the expected STEP value through all call sites, a targeted subset, or skip item 2?
- **Resolution**: All ~80 call sites — every existing `assert_deny` call gains and checks its actual expected STEP value, sourced from the preceding `write_marker`/`write_marker_at` call in the same block.
- **Source**: user

## Decision 3: Item 3 (clone-identity stamping) scope
- **Question**: Item 3's "Track this as a future hardening idea" phrasing reads as documentation rather than an implementation request. Add a code comment only, implement the mechanism now, make no code change, or file a separate tracking issue?
- **Resolution**: Implement it now — the hook wrapper stamps a durable clone identity directly into the `.bg-wait-active` marker at creation time, in addition to (not instead of) the existing `.larch-keepalive` `CLONE_PATH` fallback lookup.
- **Source**: user

## Decision 4: Item 4 (clone-ownership helper drift) remedy
- **Question**: Item 4 offers two explicit alternatives — a cross-referencing comment, or a structural equivalence test — for `clone_paths_same()`/`marker_foreign_clone()` drift between `hook-bg-poll-guard.sh` and `hook-no-progress-guard.sh`. Which remedy, or both, or skip?
- **Resolution**: Add a structural equivalence test so drift between the two hooks' copies of `clone_paths_same()` and `marker_foreign_clone()` fails CI instead of surfacing as a future incident.
- **Source**: user

## Decision 5: Fail-open vs. fail-closed philosophy must be preserved
- **Question**: Do the new clone-identity-stamping and bare-dir-deny changes need to preserve the hooks' documented fail-safe philosophy?
- **Resolution**: Yes. Both hooks are documented (`scripts/hook-bg-poll-guard.md`, `scripts/hook-no-progress-guard.md`) to fail OPEN on malformed input, missing `jq`, or unexpected runtime errors, but fail CLOSED (treat as same-clone, still block) specifically when clone identity is unknown. The new embedded clone-identity stamp is an additional signal alongside the existing `.larch-keepalive` `CLONE_PATH` lookup, not a replacement that could introduce a new false-allow path when the stamp is absent (e.g. a marker written before this change, or by an external tool).
- **Source**: codebase

## Decision 6: No shared Bash library across hooks
- **Question**: Should the structural-equivalence test eliminate the duplication by extracting `clone_paths_same`/`marker_foreign_clone` into a shared library?
- **Resolution**: No. AGENTS.md and issue #6141 itself state contract-bearing hooks stay self-contained with no shared Bash library between hooks; the test verifies the two copies stay equivalent, it does not eliminate the deliberate duplication.
- **Source**: codebase

## Decision 7: Bash 3.2 portability
- **Question**: Must new or changed Bash code in the hooks and their tests remain Bash 3.2 compatible?
- **Resolution**: Yes, per BASH_AUTHORING.md (no associative arrays, namerefs, `mapfile`, case-conversion expansions, etc.); `make lint-bash32` must stay green.
- **Source**: codebase

Record 7 decisions resolved.
