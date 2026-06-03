# Review Round 1

- Mode: `diff`
- 3 accepted, 5 rejected (3 exonerated)

## Accepted Findings

### FINDING_1: code-quality: .claude/rules/gh-body-file.md:2-32
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Deleting release-tag.yaml from paths without listing release-finish.sh/.md leaves the sole release-notes gh caller outside path-triggered gh-body-file reminders. Editors changing release-finish.sh during /release work no longer get the file-backed --notes-file / redaction reminder on path match; easier to drift from SECURITY.md outbound-redaction habits despite lint-gh-body-inline.sh covering inline --notes in .sh. Add .claude/skills/release/scripts/release-finish.sh and release-finish.md to gh-body-file.md paths: in alphabetical order after combine-issues entries.
- **Suggested revision**: Address the concern above.


### FINDING_11: **architecture** `docs/installation-and-setup.md:9` — The new sentence tells marketplace installers that GitHub Releases are cut by the operator-run `/release` skill, but `/release` is dev-only (`.claude/skills/release/SKILL.md` frontmatter: “Private to this larch repo; not plugin exported”). That page’s audience installs via `claude plugin install` and only gets exported `larch:*` skills (e.g. `/upgrade-larch` on line 32), so naming `/release` as the release source implies a skill they cannot invoke and blurs maintainer workflow vs consumer install docs. **Suggested fix:** Rephrase for installers only—e.g. that maintainers publish GitHub Releases on a release cadence (not on every merge to `main`) and that `/upgrade-larch` tracks the Latest stable release—without pointing end users at the private `/release` skill; keep `/release` naming in maintainer docs (`docs/workflow-lifecycle.md`, `scripts/promote-release.md`, `.claude/skills/release/**`).
- **Reviewer**: dyn-doc-narrative-consistency-output.txt
- **Concern**: - **architecture** `docs/installation-and-setup.md:9` — The new sentence tells marketplace installers that GitHub Releases are cut by the operator-run `/release` skill, but `/release` is dev-only (`.claude/skills/release/SKILL.md` frontmatter: “Private to this larch repo; not plugin exported”). That page’s audience installs via `claude plugin install` and only gets exported `larch:*` skills (e.g. `/upgrade-larch` on line 32), so naming `/release` as the release source implies a skill they cannot invoke and blurs maintainer workflow vs consumer install docs. **Suggested fix:** Rephrase for installers only—e.g. that maintainers publish GitHub Releases on a release cadence (not on every merge to `main`) and that `/upgrade-larch` tracks the Latest stable release—without pointing end users at the private `/release` skill; keep `/release` naming in maintainer docs (`docs/workflow-lifecycle.md`, `scripts/promote-release.md`, `.claude/skills/release/**`).
- **Suggested revision**: Address the concern above.


### FINDING_6: risk-integration: .claude/skills/release/SKILL.md:60-73
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Removed operator recovery guidance for remote tag OID mismatch while release-finish.sh still fails closed. First post-Phase-4 /release hits ERROR=remote tag exists on different commit after a legacy or manual tag on the wrong OID; operators have no documented remediation in SKILL or release-finish.md. Restore a version-agnostic recovery subsection: verify TARGET_OID plugin.json delete or move wrong remote tag with maintainer intent fetch re-run release-finish.sh.
- **Suggested revision**: Address the concern above.


