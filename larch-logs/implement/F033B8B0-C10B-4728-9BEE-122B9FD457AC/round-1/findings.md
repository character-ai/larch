### FINDING_1: code-quality: .claude/rules/gh-body-file.md:2-32
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Deleting release-tag.yaml from paths without listing release-finish.sh/.md leaves the sole release-notes gh caller outside path-triggered gh-body-file reminders. Editors changing release-finish.sh during /release work no longer get the file-backed --notes-file / redaction reminder on path match; easier to drift from SECURITY.md outbound-redaction habits despite lint-gh-body-inline.sh covering inline --notes in .sh. Add .claude/skills/release/scripts/release-finish.sh and release-finish.md to gh-body-file.md paths: in alphabetical order after combine-issues entries.
- **Suggested revision**: Address the concern above.

### FINDING_2: `c1e7530b1` — Stop per-merge release tagging (Phase 4)
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - `c1e7530b1` — Stop per-merge release tagging (Phase 4)
- **Suggested revision**: Address the concern above.

### FINDING_3: `66eba653d` — chore(larch-logs): flush implement run F033B8B0…
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - `66eba653d` — chore(larch-logs): flush implement run F033B8B0… **Scope:** Deletes `.github/workflows/release-tag.yaml` and reframes docs/rules so `/release` (`release-finish.sh` → `promote-release.sh`) is the sole tag/Release path. No `.sh` changes in the feature diff. **Plan / acceptance check (correctness lens):** | Requirement | Status | |-------------|--------| | Workflow removed | Yes | | Stale `release-tag` refs in `docs/`, `README.md`, `scripts/*.md`, `.claude/**` | Clean (only `CHANGELOG.md` history remains, per acceptance) | | `promote-release.md` / install doc match runtime | Yes — `release-finish.sh` uses `gh release create` without `--prerelease` (lines 340–341) and always calls `promote-release.sh` before success KV (lines 349–351) | | No `.sh` behavior change | Yes — diff is workflow + markdown only | | `gh-body-file.md` paths | Only `release-tag.yaml` line removed; YAML remains valid | Updated prose is consistent with actual script behavior. Removing the workflow eliminates the old push-to-`main` auto-tagger (tip SHA, prerelease, CHANGELOG notes); that is intentional product behavior, not a logic defect in the diff.
- **Suggested revision**: Address the concern above.

### FINDING_4: risk-integration: .github/workflows/release-tag.yaml (deleted)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Deleting per-merge release-tag automation removes automatic vX.Y.Z tags and GitHub Releases on every main push; only operator /release creates them now. A version-bump merge lands on main without /release; GitHub Latest and /upgrade-larch stable resolution stay on the previous cut until someone runs /release, which looks like a failed or missing release to teams used to merge-triggered tags. Confirm Phase 3 /release is on main before merge; document release discipline for maintainers; optional one-line cross-link in docs/workflow-lifecycle.md near the /release bullet.
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] risk-integration: .claude/skills/release/scripts/release-finish.sh:289-297
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Local-tag reconciliation may exit before re-probe when remote tag appears after first ls-remote; previously discussed vs release-tag.yaml race. Concurrent tag creation (manual or second /release) between probes can still hit ERROR=local tag … not TARGET_OID on paths unchanged by this PR. Re-probe remote_tag_commit_oid before local_oid != TARGET_OID branch in a follow-up touching release-finish.sh (not required for Phase 4 doc/workflow deletion).
- **Suggested revision**: Address the concern above.

### FINDING_6: risk-integration: .claude/skills/release/SKILL.md:60-73
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Removed operator recovery guidance for remote tag OID mismatch while release-finish.sh still fails closed. First post-Phase-4 /release hits ERROR=remote tag exists on different commit after a legacy or manual tag on the wrong OID; operators have no documented remediation in SKILL or release-finish.md. Restore a version-agnostic recovery subsection: verify TARGET_OID plugin.json delete or move wrong remote tag with maintainer intent fetch re-run release-finish.sh.
- **Suggested revision**: Address the concern above.

### FINDING_7: architecture: docs/installation-and-setup.md:9
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Deleting per-merge tagging creates a gap where main advances without new Releases until /release runs. Feature merges land on main but /upgrade-larch still reports latest stable at the previous cut because no new non-prerelease Release exists. Add explicit note that main merges do not publish until /release completes; cross-link release SKILL.
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: docs/installation-and-setup.md:9
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Install doc states promote to Latest happens in one run unconditionally. promote-release.sh failure leaves a Release that is not Latest while the doc implies a complete cut. Qualify with on success or normally and point to partial-failure recovery in release-finish.md.
- **Suggested revision**: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] risk-integration: .claude/skills/release/scripts/release-finish.sh:310-318
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Local-tag reconciliation can fail before post-push re-probe when remote_oid is stale. Primarily affected concurrent release-tag.yaml races; less likely after workflow removal. Pre-existing; fix with re-probe before local_oid branch if still desired.
- **Suggested revision**: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] architecture: .claude/skills/release/scripts/release-finish.md:18-19
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] mergeCommit.oid missing falls back to origin/main tip when plugin.json version matches. Running finish before mergeCommit is populated could tag main tip instead of squash merge OID. Pre-existing contract; out of Phase 4 scope.
- **Suggested revision**: Address the concern above.

### FINDING_11: **architecture** `docs/installation-and-setup.md:9` — The new sentence tells marketplace installers that GitHub Releases are cut by the operator-run `/release` skill, but `/release` is dev-only (`.claude/skills/release/SKILL.md` frontmatter: “Private to this larch repo; not plugin exported”). That page’s audience installs via `claude plugin install` and only gets exported `larch:*` skills (e.g. `/upgrade-larch` on line 32), so naming `/release` as the release source implies a skill they cannot invoke and blurs maintainer workflow vs consumer install docs. **Suggested fix:** Rephrase for installers only—e.g. that maintainers publish GitHub Releases on a release cadence (not on every merge to `main`) and that `/upgrade-larch` tracks the Latest stable release—without pointing end users at the private `/release` skill; keep `/release` naming in maintainer docs (`docs/workflow-lifecycle.md`, `scripts/promote-release.md`, `.claude/skills/release/**`).
- **Reviewer**: dyn-doc-narrative-consistency-output.txt
- **Concern**: - **architecture** `docs/installation-and-setup.md:9` — The new sentence tells marketplace installers that GitHub Releases are cut by the operator-run `/release` skill, but `/release` is dev-only (`.claude/skills/release/SKILL.md` frontmatter: “Private to this larch repo; not plugin exported”). That page’s audience installs via `claude plugin install` and only gets exported `larch:*` skills (e.g. `/upgrade-larch` on line 32), so naming `/release` as the release source implies a skill they cannot invoke and blurs maintainer workflow vs consumer install docs. **Suggested fix:** Rephrase for installers only—e.g. that maintainers publish GitHub Releases on a release cadence (not on every merge to `main`) and that `/upgrade-larch` tracks the Latest stable release—without pointing end users at the private `/release` skill; keep `/release` naming in maintainer docs (`docs/workflow-lifecycle.md`, `scripts/promote-release.md`, `.claude/skills/release/**`).
- **Suggested revision**: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] architecture
- **Reviewer**: dyn-doc-narrative-consistency-output.txt
- **Concern**: - **architecture** — Across `release-finish.md`, `SKILL.md` Step 6, and `scripts/promote-release.md` Purpose/Edit-in-sync, the reframed story is aligned: `release-finish.sh` creates tag + Release (`gh release create` without `--prerelease` at `.claude/skills/release/scripts/release-finish.sh:340`), then calls `promote-release.sh` (`:349-351`); partial-failure and promote-only retry paths match; no edited file still describes per-merge `release-tag.yaml` or prerelease-by-default cuts.
- **Suggested revision**: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: dyn-doc-narrative-consistency-output.txt
- **Concern**: - **risk-integration** `.claude/skills/release/scripts/release-finish.sh:289-297` — Pre-existing local-tag reconciliation can still fail closed if a remote tag appears between probes; removing `release-tag.yaml` race docs does not change script behavior, only drops workflow-specific recovery prose (intentional per plan).
- **Suggested revision**: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] architecture
- **Reviewer**: dyn-doc-narrative-consistency-output.txt
- **Concern**: - **architecture** `.claude/rules/gh-body-file.md` — `release-finish.sh` uses `--notes-file` but was not added to the rule’s `paths:` list (pre-existing; unrelated to this diff’s single-line removal).
- **Suggested revision**: Address the concern above.

