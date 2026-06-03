---
name: bump-version
description: Use when applying a version bump on a feature branch (manual or via /release). Classify and apply a semantic version bump based on the current branch diff. Updates .claude-plugin/plugin.json and commits exactly one version-only commit. Not invoked by /implement after Phase 1 (#3364). Only inspects the public plugin surface (skills/**, agents/**) — changes under .claude/** default to PATCH.
allowed-tools: Bash, Read
---

# Bump Version

Classify and apply a semantic version bump for this PR. This is a development-only skill (not on the `/implement` ship path after Phase 1 #3364). It produces exactly ONE commit: a version-only edit of `.claude-plugin/plugin.json`.

## Classification rules

The classifier inspects **only the public plugin surface** — `skills/**` and `agents/**`. Changes under `.claude/**`, `scripts/**`, `hooks/**`, `docs/**`, `.github/**`, `CHANGELOG.md`, etc. do not contribute to MAJOR/MINOR classification and default the bump to PATCH.

Severity hierarchy: **MAJOR > MINOR > PATCH** (highest wins).

### MAJOR — backward-incompatible changes
Any of the following in `skills/**` or `agents/**`:
- A deleted `skills/*/SKILL.md` or `agents/*.md`
- A renamed `skills/*/SKILL.md` (git status `R`)
- A changed `name:` frontmatter field in an existing SKILL.md
- A `--<flag>` token removed from a SKILL.md's `argument-hint:` frontmatter field (token-set comparison; wording-only edits to the argument-hint that preserve all tokens do not count)

### MINOR — backward-compatible additions
Any of the following in `skills/**` or `agents/**` (only if not MAJOR):
- A newly added `skills/*/SKILL.md` or `agents/*.md`
- A `--<flag>` token added to a SKILL.md's `argument-hint:` frontmatter field

### PATCH — everything else
Default for all other changes when this skill runs (manual operator or `/release`). `/implement` post-Phase 1 (#3364) does not require a per-PR bump on the ship path.

## Caveat — escalation-only clause

After `classify-bump.sh` computes its deterministic baseline, the main agent (you) reviews the full diff for **behavioral** changes that a reasonable client would judge as unexpectedly backward-incompatible relative to a skill's original intent — even when no signature changed.

**You may ONLY escalate severity (PATCH → MINOR → MAJOR). Never downgrade.**

If you escalate, append at most 5 sentences (≤100 words) to the reasoning log file explaining why. State the specific evidence — do not restate the diff or summarize the classifier's bullets. **If you do not escalate, write nothing — do not append to the log, do not summarize the diff, do not narrate your decision.** Escalation is rare; the deterministic classifier is correct in the common case.

## How it works

1. The operator or `/release` (Phase 3) invokes this skill — not `/implement` post-Phase 1.
2. The skill runs `classify-bump.sh`, which:
   - Fetches `origin/main` (best-effort, non-fatal on failure)
   - Resolves `BASE` via `main` → `origin/main` fallback
   - Validates `.claude-plugin/plugin.json` via `jq`
   - Detects an **already-bumped branch** by checking whether HEAD, after walking past up to three transparent bump-pipeline commits, is a commit with subject `^Bump version to [0-9]+\.[0-9]+\.[0-9]+$`. Transparent commits are limited to `Update CHANGELOG for X.Y.Z` commits that touch only `CHANGELOG.md` and `chore(larch-logs): ...` commits that touch only `larch-logs/**`; subject matches alone are not trusted. If so, emits `BUMP_TYPE=NONE` and exits 0 (no-op). If a bump exists earlier in the branch but additional non-transparent commits have landed on top, a fresh bump is required.
   - Computes `git diff -M --name-status $BASE HEAD -- skills agents` for file-level classification (added/deleted/renamed SKILL.md and agent files)
   - For each modified SKILL.md, reads the old and new full file contents via `git show "$BASE:<path>"` and `git show "HEAD:<path>"`, extracts the first YAML frontmatter block between `---` markers, and compares the `name:` and `argument-hint:` fields. The `argument-hint:` comparison uses token sets: a `--<flag>` present in both old and new is treated as unchanged; only genuine additions or removals contribute to classification.
   - Writes evidence to `${IMPLEMENT_TMPDIR:-${TMPDIR:-/tmp}}/bump-version-reasoning.md` (absolute path also emitted as `REASONING_FILE=<path>` on stdout)
   - Maintains its sibling contract at `$PWD/.claude/skills/bump-version/scripts/classify-bump.md`; update that file with idempotency or classification behavior changes.
   - Emits `KEY=VALUE` lines on stdout: `CURRENT_VERSION`, `NEW_VERSION`, `BUMP_TYPE`, `REASONING_FILE`
3. You (main agent) parse the output and review the diff for the **escalation-only** caveat (line 34). **Do not write commentary about that review unless you actually escalate** — no log append, no diff summary, no narration. If escalating, update `NEW_VERSION` and append the bounded reasoning per the Caveat above; otherwise proceed directly to `apply-bump.sh` with the emitted `NEW_VERSION`.
4. You invoke `apply-bump.sh --new-version <NEW_VERSION>`, which:
   - First verifies the working tree is clean (fails on any staged, unstaged, or untracked changes). Dirty-worktree failures include `/implement` phantom-file guidance pointing operators at the tracking issue Execution Issues section or the literal `\$IMPLEMENT_TMPDIR/execution-issues.md` path; the backslash keeps manual `set -u` invocations from expanding an unset variable.
   - Backs up `.claude-plugin/plugin.json`
   - Rewrites the `version` field via `jq` (atomic via tmp + mv)
   - Runs `git add`, then `git fetch origin main` before `git commit`. Fetch failure is fatal with rollback: restore from `$BACKUP`, `git reset HEAD "$PLUGIN_JSON"`, and emit `ERROR="git fetch origin main failed; cannot verify origin/main version guards"`.
   - Reads `origin/main:.claude-plugin/plugin.json`'s version with strict semver validation. Parse failure is fatal with the same rollback.
   - If the parsed origin version equals `NEW_VERSION`, rolls back the staged `plugin.json` mutation and calls `fail()` with `ERROR="origin/main has already bumped to <NEW_VERSION>; re-classify needed"`.
   - If `NEW_VERSION < ORIGIN_VERSION`, rolls back the staged `plugin.json` mutation and fails closed on the version-regression guard with `ERROR="version regression: <NEW_VERSION> < origin/main <ORIGIN_VERSION>; rebase conflict may have been resolved to branch stale version — re-resolve and re-bump"`.
   - `git commit -m "Bump version to <NEW_VERSION>"`
   - `CHANGELOG.md` updates are owned by `/release` (Phase 3), not `/implement` post-Phase 1.
   - Rolls back from backup on commit failure
   - Maintains its sibling contract at `$PWD/.claude/skills/bump-version/scripts/apply-bump.md`; update that file with any behavioral change.
5. If `BUMP_TYPE=NONE`, skip the apply step and report "already bumped".

**Fetch-failure asymmetry (intentional, do not harmonize)**: `classify-bump.sh` treats `git fetch origin main` failure as non-fatal because the classifier can degrade to a stale baseline and the caller still has later freshness gates. `apply-bump.sh`'s pre-commit probe treats fetch failure as fatal with rollback because the same-version probe is meaningless against a stale view, and landing a duplicate bump commit is worse than halting.

## Usage

```bash
${CLAUDE_PLUGIN_ROOT_PLACEHOLDER:-$PWD}/.claude/skills/bump-version/scripts/classify-bump.sh
```

Parse the output for `CURRENT_VERSION`, `NEW_VERSION`, `BUMP_TYPE`, `REASONING_FILE`.

If `BUMP_TYPE=NONE`, report the no-op and exit.

Otherwise, review the branch diff for the escalation-only caveat (above) and decide whether to escalate. **Do not write commentary about that review unless you actually escalate** — no log append, no diff summary, no narration. If escalating, compute the new version from `CURRENT_VERSION` + your escalated bump type and append the bounded reasoning per the Caveat above; otherwise invoke `apply-bump.sh` directly with the script-emitted `NEW_VERSION`.

Then apply:

```bash
$PWD/.claude/skills/bump-version/scripts/apply-bump.sh --new-version <NEW_VERSION>
```

## Output contract

The reasoning log at `${IMPLEMENT_TMPDIR:-${TMPDIR:-/tmp}}/bump-version-reasoning.md` may be archived to committed `larch-logs/` by `/release` or manual workflows. `/implement` no longer runs `implement-finalize.sh postbump` changelog or version-bump-reasoning batches (Phase 1 #3364). The absolute path of the reasoning log is also emitted on stdout by `classify-bump.sh` as `REASONING_FILE=<path>` — callers should prefer that structured output over reconstructing the path from env vars.

## Exit codes
- `classify-bump.sh` — 0 on success (including `BUMP_TYPE=NONE`), non-zero on parse/validation failure
- `apply-bump.sh` — 0 on successful commit, non-zero on dirty worktree, origin/main probe failure (including fetch failure for either version guard), same-version race, version-regression guard failure (`NEW_VERSION < ORIGIN_VERSION`), parse failure, or commit failure (rollback performed after mutation)
