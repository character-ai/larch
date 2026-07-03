## Proposed Design Outline

### Goals
- Close the bare `$dir`-only Bash probe gap in `hook-bg-poll-guard.sh` (currently allowed) and add a same-clone regression test asserting deny.
- Strengthen `assert_deny()` in `scripts/test-hook-bg-poll-guard.sh` to verify the actual marker STEP value at every existing call site.
- Stamp a durable clone identity into `.bg-wait-active` markers at creation time, and add a structural equivalence test guarding `clone_paths_same()`/`marker_foreign_clone()` drift between `hook-bg-poll-guard.sh` and `hook-no-progress-guard.sh`.

### Non-goals
- Eliminating the deliberate duplication between the two hooks (no shared Bash library for hooks).
- Extending the structural-equivalence test to the other duplicated helpers (`marker_value`, `canonical_dir`, `marker_candidates`, `marker_step_completed`/`is_step_completed`) beyond the two named clone-ownership functions.
- Changing existing sentinel-release logic or STEP-value semantics at marker-creation call sites.

### Approach sketch
- Add an unconditional bare-dir-match trigger in `hook-bg-poll-guard.sh`'s main deny loop (alongside the 7 existing gated triggers) so a command consisting only of the literal marker directory path also denies.
- Add an optional expected-step parameter to `assert_deny()`; thread the real expected STEP value through every existing call site plus the new bare-dir test.
- Add a `CLONE_PATH`-equivalent field written into `.bg-wait-active` at creation time (reusing the same canonicalization logic `.larch-keepalive` already uses); update `marker_foreign_clone()` in both hooks to prefer the embedded field, falling back to `.larch-keepalive` when absent.
- Add a new structural-equivalence test comparing the two hooks' copies of `clone_paths_same()`/`marker_foreign_clone()`.
- Update sibling `.md` docs for every behavior change (script-md-siblings rule).

### Surfaces in scope
- `scripts/hook-bg-poll-guard.sh`, `scripts/hook-bg-poll-guard.md`
- `scripts/test-hook-bg-poll-guard.sh`, `scripts/test-hook-bg-poll-guard.md`
- `scripts/hook-no-progress-guard.sh`, `scripts/hook-no-progress-guard.md`
- Marker-creation call sites across `/design` and `/implement` (exact file list pending direct inspection)
- New structural-equivalence test script + Makefile wiring

### Open questions
- None.
