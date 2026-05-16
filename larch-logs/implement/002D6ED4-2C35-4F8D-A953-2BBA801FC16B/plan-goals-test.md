## Goal
Add shellcheck to SKIP list in lint job and update four comment blocks to complete Phase 2 of the shellcheck CI split

## Implementation Plan

**Goal**: Complete Phase 2 of the shellcheck split in `.github/workflows/ci.yaml` — add `shellcheck` to the `SKIP` list in the `lint` job and update four comment blocks to drop Phase 1/Phase 2 language.

**Files to modify**: `.github/workflows/ci.yaml` (only)

### Change 1 — Add `shellcheck` to the `SKIP` env (line 64)
Before: `SKIP: agnix,lint-mermaid-fences`
After:  `SKIP: agnix,lint-mermaid-fences,shellcheck`

### Change 2 — Rewrite the `lint` job header comment (lines 23–35)
- Remove `shellcheck` from the prose list of hooks run by this job.
- Remove the Phase 1/Phase 2 rollout paragraph.
- Add a sentence explaining shellcheck is SKIPped here because the dedicated `shellcheck` job runs it in parallel — mirroring the existing `agnix` treatment.
- Keep the gitleaks rationale, test-harnesses split, and lint-mermaid split notes unchanged.

### Change 3 — Extend the inline SKIP comment (lines 55–62)
- Mention both `agnix` and `shellcheck` as SKIPped because their dedicated jobs run them in parallel.
- Keep the "pre-commit hook remains active for local `pre-commit run` and the dev git-hook" language (applies to both).
- Keep the "If the dedicated job is removed, drop its name from SKIP" warning (generalized to both).
- Keep the `gitleaks` non-skip rationale and Issue #1034 reference.

### Change 4 — Rewrite the `shellcheck` job header comment (lines 133–138)
- Drop the Phase 1/Phase 2 rollout language.
- State: runs in parallel with `lint`; `lint` SKIPs shellcheck to avoid paying the pre-commit env-install cost twice; shared `pre-commit-${{ hashFiles('.pre-commit-config.yaml') }}` cache key means the shellcheck hook env is restored from cache when both jobs run.


## Test plan
- Run `/relevant-checks` after edits.
- Expected: `actionlint` and `markdownlint` pass; no pre-commit linter errors.
- Sanity: `SKIP=agnix,lint-mermaid-fences,shellcheck pre-commit run --all-files` should show `shellcheck` as Skipped.
