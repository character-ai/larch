# test-design-pause-resume.sh contract

Offline regression harness for `/design` pause/resume helpers. It stubs `gh`,
`git fetch`, `git ls-tree`, `git show`, and `design-log-publish.sh` so the
round-trip runs without network access.

Primary contracts live in:

- `scripts/named-block-write.md`
- `scripts/design-pause-save.md`
- `scripts/design-pause-load.md`

## Gate-B-bypass empty-state coverage

The harness includes `gate B bypass writes dual sentinels from empty state`: start with no `step-3` or `step-3.5` sentinels; invoke `apply_gate_b_bypass_sentinels`; assert both exist; then save/load and expect `PAUSE_OK=true`, `LOAD_OK=true`, and `STEP=3b`. A separate case seeds only `step-3`, invokes the helper to add `step-3.5`, and asserts the same save/load `STEP=3b` contract.

Do not satisfy this case by calling `complete_design_steps … 3 3.5` or by manually pre-touching sentinels before the helper runs. Pre-written-layout save/load coverage remains separate.

## Legacy compatibility coverage

- Legacy SIMPLE snapshots with `.completed/step-2a` but no `.completed/step-2a.5` save/load at `STEP=2a.5`, then execute the Step 2a.5 compatibility repair and assert the missing marker is written.
- Legacy snapshots with `.completed/step-3b` but no `.completed/finalize` save/load at `STEP=4`, then execute the Step 4 FINALIZE compatibility guard and assert `.completed/finalize` is written.
- FINALIZE failure coverage pins the operator-visible warning `**⚠ FINALIZE failed; repair the missing artifact before Step 5.**` and the non-zero exit path.

## Recent contract coverage

- Covers malformed and argv-precedence `--repo` failures, contradictory publish envelopes, and exit-1 recovery branches that remain resumable.
- Covers real-git export-ignore restoration in a stub-free-PATH subshell that
  `cd`s into the initialized repo so `git rev-parse` binds `REPO_TOP` to the
  snapshot worktree.
- Covers marker delete-on-success for round-trip and body-drift resumes,
  restored `.pause-requested` cleanup, `MARKER_CLEARED=true|false`, and
  `WARN=marker-delete-failed` when post-success marker deletion fails.
- Covers marker keep-on-failure for late-step and deleted-subtree empty
  enumeration `missing-restored-artifact` paths plus dedicated
  `snapshot-extract-failed` fixtures for failed `ls-tree` and per-path
  `git show`.

## Phase 7 folded-discussion and route regression

Pause snapshots created during an in-flight pause request may legitimately
include `.pause-requested`. Each regression case that exercises post-restore
cleanup must assert the marker existed in the published snapshot **before**
`design-pause-load.sh` runs, then assert the restored live
`$DESIGN_TMPDIR/.pause-requested` is absent afterward so resume does not
immediately re-pause.

| Fixture | Intent |
|---------|--------|
| Folded discussion through `step-1e` | Resume routes forward to `STEP=2a` (not replay discussion); snapshot retains `.outline-approved` and discussion sentinels. |
| Direct-review Step 3 entry | With `.step3-reentry` present, Step 3 entry restores `step-2a`/`step-2a.5`/`step-2b`/`step-2b.5`, consumes the marker, and resumes at `STEP=3`. |
| No-brainstorm Step 2a entry | Discussion sentinels through `step-1d.7` without `step-1d.5`; Step 2a entry repair writes `step-1d.5` before pause-save. |
| Backward-loop re-entry clear host | Stale `step-1e`…`step-4b` markers are removed before save; resume lands at `STEP=1e` or, after direct-review restoration, `STEP=3` — not Gate C or a later folded host. |
| Already-planned Q&A-only terminal | Contiguous prefix through `step-1d.5` (`step-1c`, `step-1d`, and `step-1d.5`), not only the non-contiguous `step-1d.5` marker; resume at `STEP=1d.7`. |
