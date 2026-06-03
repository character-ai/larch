## Goal
Implement issue #3367: [IMPLEMENTING] Versioning Overhaul Phase 4: Stop per-merge tagging in release-tag.yaml\n\n# Versioning Overhaul Phase 4 — Stop per-merge tagging in `release-tag.yaml`.

## Implementation Plan
## Plan

**Tier**: SIMPLE. Smallest change that stops per-merge tagging and removes every stale `release-tag.yaml` reference. One workflow deletion plus doc/rule reframes. No behavioral code changes.

**Depends on Phase 3** (`/release` owns tag + Release creation) — already landed as #3366 (CLOSED). No dependency on Phase 2 / #3365.

### REMOVED: `.github/workflows/release-tag.yaml`
Delete the workflow in full. Its three responsibilities are all superseded by the operator-run `/release` skill (`release-finish.sh`, landed in Phase 3):
- per-merge `vX.Y.Z` tag → now `/release`
- per-merge prerelease GitHub Release (`--latest=false --prerelease`) → now `/release`
- "Extract changelog entry" step (reads `CHANGELOG.md`) → release notes are now LLM-composed by `/release` Step 3
No downstream workflow consumes the tags/Releases this creates: only `ci.yaml` remains and it is not `on: push: tags:` / `on: release:` triggered.

### UPDATED: `scripts/promote-release.md`
- "## Purpose": replace "Every merge to main creates a GitHub Release with `--latest=false --prerelease` (via `.github/workflows/release-tag.yaml`)." Say the operator-run `/release` skill (`release-finish.sh`) creates the tag and the Release and normally promotes to "Latest" in the same run (it invokes `promote-release.sh` at the end of `release-finish.sh`); `promote-release.sh` also promotes an existing version to "Latest" and clears any pre-release flag when used standalone (retry after partial finish, legacy releases, or promote-only). Do not imply operators must manually promote every cut or that `/release` leaves new Releases prerelease by default.
- "## Edit-in-sync": replace the `.github/workflows/release-tag.yaml` line with `.claude/skills/release/scripts/release-finish.sh` (the Release creator). Keep the `docs/installation-and-setup.md` entry.
- Do NOT change `promote-release.sh` behavior.

### UPDATED: `.claude/skills/release/SKILL.md`
- Step 6 pointer (the `release-finish.md` "See ... idempotency vs `release-tag.yaml`" line): drop "vs `release-tag.yaml`"; reframe as "`TARGET_OID` resolution and idempotent re-run safety".
- Remove the "Recovery when `release-tag.yaml` tags `origin/main` tip but finish targets `mergeCommit.oid`" paragraph. The per-merge auto-tagger no longer exists, so that workflow race cannot occur; `/release`'s single-runner model and `release-finish.sh` idempotency cover legitimate re-runs.

### UPDATED: `.claude/skills/release/scripts/release-finish.md`
Docs-only reframe — `release-finish.sh` behavior is unchanged (its idempotent tag re-check / fail-closed logic stays; it is still valuable for `/release` re-runs and manual tag ops):
- Tag-idempotency bullets: drop the "(idempotent re-run after `release-tag.yaml`)" and "(TOCTOU vs `release-tag.yaml`)" attributions. Reframe as idempotent re-run / concurrent-write safety.
- Remove the "## release-tag.yaml race" section (moot once the workflow is gone).
- "## GitHub Release": drop the "(e.g. `release-tag.yaml` race)" example on the `gh release edit` bullet.

### UPDATED: `.claude/rules/gh-body-file.md`
Remove the `".github/workflows/release-tag.yaml"` entry from the `paths:` frontmatter list. Leave every other path entry and the ordering intact. (Maintenance section already requires listing only files that invoke `gh ... --notes-file`; the deleted workflow no longer qualifies.)

### UPDATED: `docs/installation-and-setup.md`
Add one short sentence near the "Latest stable release" section: GitHub Releases are cut by the operator-run `/release` skill (tag, Release, and promote to "Latest" in one run), not auto-created on every merge to `main`. No other change — the doc had no per-merge-release prose to fix; this is a small additive clarification so readers understand where Releases come from.

### Verify-only (no edit expected)
`README.md`, `docs/configuration-and-permissions.md`, `.github/workflows/ci.yaml`. Grepped: none reference `release-tag.yaml` or the per-merge-release model. Re-confirm clean after the edits land.

### Approach
Docs + one workflow file. The single behavioral change is the deletion of `release-tag.yaml`, which removes the per-merge tag/Release automation. Everything else is prose that pointed at that workflow or described the per-merge model; reframe it to the `/release`-driven model. Preserve the `.sh` scripts (`promote-release.sh`, `release-finish.sh`) byte-for-byte in behavior — only their `.md` contracts and `SKILL.md` prose change. Reframe (do not delete) defensive idempotency notes: the *why* shifts from "race against the auto-tagger" to "idempotent re-run safety", but the documented behavior the scripts implement is unchanged.

### Edge cases
- **gh-body-file.md paths YAML**: remove exactly one list item; keep the block valid YAML and its existing ordering. Do not disturb adjacent entries.
- **markdownlint** (MD038/MD037/MD001) on every edited `.md`: keep backtick spans free of inner whitespace; no heading-level jumps when removing the recovery paragraph / race section.
- **actionlint**: after deletion, `make lint` runs actionlint over the remaining workflows (`ci.yaml` only) — must stay green.
- **promote-release.md Purpose**: `release-finish.sh` uses `gh release create` without `--prerelease` and then calls `promote-release.sh`; prose must not mirror the deleted workflow's prerelease-then-manual-promote story.
- **Stale-attribution residue**: the `release-tag.yaml` token appears multiple times within `release-finish.md` and `SKILL.md`; remove/reframe every occurrence in the edited files, not just the first.

### Failure modes
1. **Missed reference** — one `release-tag.yaml` mention left in `.claude/skills/release/**` or the paths glob. Earliest signal: the Acceptance grep gate. Mitigation: run the repo-wide grep before declaring done.
2. **Over-reach into `.sh` behavior** — accidentally stripping the idempotency/fail-closed logic from `release-finish.sh` while reframing its `.md`. Signal: a diff touching `release-finish.sh` or `promote-release.sh`. Mitigation: edits restricted to `.md`/SKILL/workflow; assert no `.sh` diff.
3. **Wrong paths-glob line removed** — deleting an unrelated `gh-body-file.md` paths entry. Signal: pre-commit path-rule coverage / review. Mitigation: remove only the `release-tag.yaml` line; diff-review the frontmatter.

### Testing strategy
- `make lint` (actionlint over remaining workflows, markdownlint over edited `.md`, agent-lint) — must pass.
- `bash scripts/relevant-checks.sh` — must pass.
- Acceptance grep gate (manual + reviewable): a repo-wide `grep` for `release-tag` excluding `.git`, `larch-logs`, and `node_modules` returns only historical `CHANGELOG.md` lines.
- No new unit tests: no script behavior changes. Confirm no existing harness asserts `release-tag.yaml` exists (verified none today).

## Acceptance

- `.github/workflows/release-tag.yaml` no longer exists.
- `make lint` passes (including actionlint over the remaining workflows, markdownlint, agent-lint).
- No remaining reference to `release-tag.yaml` in `docs/`, `README.md`, `scripts/*.md`, or `.claude/**` (historical `CHANGELOG.md` mentions excepted).
- `scripts/promote-release.sh` and `.claude/skills/release/scripts/release-finish.sh` have no behavior change (no `.sh` diff for either).
- `scripts/promote-release.md` and `docs/installation-and-setup.md` describe `/release` as the tag/Release creator with normal in-run promote to "Latest"; the per-merge-release and prerelease-by-default wording is gone.

diff_lines: 148

## Test plan
(no test plan section in plan-file)
