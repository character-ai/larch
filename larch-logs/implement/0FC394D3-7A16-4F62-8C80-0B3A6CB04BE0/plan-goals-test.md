## Goal
Implement issue #3404: [IMPLEMENTING] [OOS] Python ship path lacks bash exit-4 ship_pr_pre_push conflict handoff\n\n## Out-of-Scope Observation.

## Implementation Plan
## Plan

Add a python-path equivalent of the bash exit-4 `ship_pr_pre_push` conflict handoff. This is a
**library-level representation only** — `python/` is dev/CI-only until Phase 7, with no driver,
state layer, CLI, or exit-code emission. A future Phase 7 driver translates the new signal to the
bash exit-4 contract.

### Files to modify (all under `python/`)

#### `python/config.py`
Add three bash-identical literal constants (single source of truth):
- `SHIP_PR_RRR_RESUME_PHASE = "ship-pr-rrr-phase14"`
- `SHIP_PR_PRE_PUSH_CALLER_KIND = "ship_pr_pre_push"`
- `SHIP_PR_RRR_AFTER_PHASE14_FLAG_BASENAME = "ship-pr-rrr-after-phase14.flag"`

`ENV_LARCH_BUMP_FILES` already exists and is reused by the non-bump-only gate.

#### `python/errors.py`
Add `PrePushConflictHandoff(Stalled)` carrying `conflict_files: tuple[str, ...]`, `resume_phase`,
`caller_kind`, plus a `conflict_csv` property (the bash `CONFLICT_FILES` shape). Keep `errors.py`
stdlib-only / config-free — the caller (`rebase.py`) supplies the tokens from `config`.

#### `python/rebase.py`
- Import: drop now-unused `NeedsUserInput`, add `PrePushConflictHandoff`.
- Add `_is_bump_path(path)` + `_conflicts_are_non_bump_only(paths)` mirroring bash
  `ship_pr_vendor_conflict_csv_is_non_bump_only`: true only when **no** conflict path is a bump file
  (CHANGELOG.md / CHANGELOG.rst / CHANGELOG, `.claude-plugin/plugin.json`, version.go, go.sum, or any
  `LARCH_BUMP_FILES` entry). Reuse `_CHANGELOG_BASENAMES` + `_is_plugin_json_path`.
- Add `_write_handoff_flag(tmpdir)` resolving `<tmpdir or $IMPLEMENT_TMPDIR>/ship-pr-rrr-after-phase14.flag`;
  raise `Stalled` if the dir is unresolvable or the write fails.
- Thread `tmpdir: str | None = None` into `_resolve_conflicts`; pass `tmpdir=tmpdir` from
  `rebase_and_rebump`.
- **Site 1** (`waterfall.winning_tier is None`): when `_conflicts_are_non_bump_only(tuple(remaining))`,
  write the flag and raise `PrePushConflictHandoff(conflict_files=tuple(remaining), resume_phase=..., caller_kind=...)`;
  otherwise (bump-only / mixed) raise plain `Stalled` — no flag, no tokens.
- **Site 2** (a tier reported success but `_unmerged_paths(...)` still returns conflicts): raise plain
  `Stalled` — no handoff, no flag.

#### `python/README.md`
Note the new `PrePushConflictHandoff` + flag behavior (site-1, non-bump-only only; all other
exhaustion paths raise plain `Stalled`) and the Phase 7 deferral (no exit-4, state writes,
`CONFLICT_FILES` emit, or `--resume-phase` parsing).

#### Tests
- `python/test_config.py`: assert the three constants equal the exact bash literals.
- `python/test_errors.py`: assert `PrePushConflictHandoff` subclasses `Stalled` / `ShipError`; assert
  field storage + the `conflict_csv` property.
- `python/test_rebase.py`: update the two existing waterfall-exhaustion tests to expect
  `PrePushConflictHandoff` (+ flag written + tokens + `conflict_files`); add tests for bump-only
  exhaustion -> `Stalled` (no flag), site 2 -> `Stalled`, and unresolvable handoff dir -> `Stalled`.

### Bash fidelity (two parity rules)
1. Handoff fires only when the in-process fixer waterfall fails (site 1) — mirrors the failure branch
   of bash `run_recovery_waterfall`. Site 2 is a later plain `exit_stall` in bash, so python raises
   plain `Stalled` there.
2. Handoff fires only for non-bump-only conflicts — mirrors `ship_pr_vendor_conflict_csv_is_non_bump_only`.
   Subclass `Stalled` because bash `exit_stall` = exit 4 = `config.EXIT_BAIL`; a Phase 7 driver
   pattern-matches the subtype to write `RESUME_PHASE`/`CALLER_KIND`, emit `CONFLICT_FILES`, exit 4,
   and dispatch `conflict-resolution.md`.

### Out of scope (Phase 7)
- python driver / CLI / state layer; the actual `exit 4`; `RESUME_PHASE`/`CALLER_KIND` state writes;
  `emit_kv CONFLICT_FILES`; `--resume-phase ship-pr-rrr-phase14` parsing + flag-required validation.
- No edits to `scripts/ship-pr.sh`, `skills/implement/references/conflict-resolution.md`, or
  `skills/implement/SKILL.md`.

## Acceptance

- `python/config.py` defines `SHIP_PR_RRR_RESUME_PHASE="ship-pr-rrr-phase14"`,
  `SHIP_PR_PRE_PUSH_CALLER_KIND="ship_pr_pre_push"`, and
  `SHIP_PR_RRR_AFTER_PHASE14_FLAG_BASENAME="ship-pr-rrr-after-phase14.flag"`.
- `python/errors.py` defines `PrePushConflictHandoff(Stalled)` with `conflict_files`, `resume_phase`,
  `caller_kind`, and a `conflict_csv` property.
- In `python/rebase.py`, in-process fixer-waterfall exhaustion (site 1) on non-bump-only conflicts
  writes `ship-pr-rrr-after-phase14.flag` and raises `PrePushConflictHandoff` carrying the conflict
  files and the `config` tokens.
- Bump-only / mixed exhaustion (site 1), the "conflicts remain after a winning tier" case (site 2),
  and an unresolvable / unwritable handoff dir all raise plain `Stalled` — no flag, no handoff tokens.
- `rebase.py` no longer raises `NeedsUserInput` (import dropped).
- `make py-test` and `make py-lint` pass; `python/test_stdlib_only.py` stays green; new/updated tests
  in `test_config.py`, `test_errors.py`, `test_rebase.py` cover all cases above.
- No changes to `scripts/ship-pr.sh`, `skills/implement/references/conflict-resolution.md`, or
  `skills/implement/SKILL.md`.

diff_lines: 177

## Test plan
(no test plan section in plan-file)
