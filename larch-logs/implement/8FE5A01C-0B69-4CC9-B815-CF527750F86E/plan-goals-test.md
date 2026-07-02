## Goal
Implement issue #6020: [IMPLEMENTING] [BUG] SECURITY.md and skill prose stale after #5888, #5973, #5982 behavior changes.

## Implementation Plan
## Summary

Three merged PRs changed security-relevant behavior without updating SECURITY.md, and #5888 also left two runtime skill prose passages describing the old review-fix lane order. AGENTS.md requires SECURITY.md updates when security-relevant behavior changes. A security review relying on SECURITY.md's lane and hook enumeration now reaches wrong conclusions about which vendors can write the tree, which SessionStart hooks run, and what orchestrators read on check failures.

## Original report

From the 2026-07-02 post-merge audit at 63ed17f18. All four SECURITY.md passages and both skill passages were verified stale by direct read. In the #5982 run a reviewer flagged the SECURITY.md gap at severity "important" (OOS_2) and it was dropped before the vote; no follow-up was filed.

## Reproduction scenario

Read the six passages listed under Evidence and compare each with shipped behavior at 63ed17f18 (registry order in python/larch/core/config.py, the launch-claude-review-fix launcher, hooks/hooks.json hook order, and the DIGEST_FILE envelope key emitted by checks run-relevant).

## Expected behavior

- SECURITY.md "External tool delegation" and "Review fix application" describe the review-fix coder lane as Codex, then Cursor, then a write-capable Claude lane (`agent launch-claude-review-fix`, Read/Edit/Write allowed), documented like the existing write-capable `launch-claude-ci` paragraph.
- SECURITY.md's SessionStart hook enumeration includes scripts/cleanup-sessionstart.sh with its deletion scope, and hook ordinals are correct or removed.
- SECURITY.md "Relevant-checks captured logs" documents the `DIGEST_FILE` artifact and its consumption order relative to `REDACTED_LOG_FILE`.
- Skill prose matches the registry order.

## Observed behavior

- SECURITY.md line 183 ("External tool delegation"): "The review-fix coder lane is Cursor-first (Cursor -> Codex -> main agent, #3704)." Stale after #5888: the registry is Codex, Cursor, Claude (python/larch/core/config.py:472) and the new write-capable Claude lane is unmentioned.
- SECURITY.md line 206 ("Review fix application"): "applies fixes through Cursor, then Codex (#3704), while the main agent does not use Edit/Write for review fixes." Both clauses stale after #5888.
- SECURITY.md line 236 ("SessionStart background admin-merge sweep"): calls sweep-design-logs.sh "the second SessionStart hook registered in hooks/hooks.json". After #5973 the order is sessionstart-health.sh, cleanup-sessionstart.sh, sweep-design-logs.sh. The new cleanup hook, which automatically deletes aged entries under $TMPDIR, /tmp, and ~/.cache/larch/sessions on every session event, has no security section anywhere in SECURITY.md.
- SECURITY.md line 238 ("Relevant-checks captured logs"): "orchestrators are instructed to read REDACTED_LOG_FILE, not raw LOG_FILE". After #5982 orchestrators are instructed digest-first via DIGEST_FILE; the digest artifact (mode 0600, built only from the redacted log) is undocumented.
- skills/review-and-fix/SKILL.md:12: "dispatches Cursor, then Codex (#3704)". Stale.
- skills/implement/references/step5-review-branches.md:47: "(Cursor -> Codex both exhausted)" in the coder-main-agent-required branch the main agent reads. Stale; instructions remain functionally correct.

## Root cause analysis

Each PR's plan carried a SECURITY.md item as MAY_UPDATE or "verify, edit if stale" and the implementation skipped it. Reviewers caught it once (#5982 run, OOS_2) and the finding was dropped pre-vote. Observation, not inference: passages are stale at HEAD, and git history since each merge shows no SECURITY.md follow-up commit.

## Evidence

- Direct reads of SECURITY.md lines 183, 206, 236, 238 at 63ed17f18 (audit re-verified all four).
- python/larch/core/config.py:472: review.fix_coder order codex, cursor, claude.
- python/larch/agents/_ci_launcher.py: `launch_claude_review_fix_main` with `--allowedTools Read,Edit,Write` (lint-fix parity).
- hooks/hooks.json: three SessionStart hooks in order health, cleanup, sweep.
- Run log larch-logs/implement/454633C3-5D3B-4678-818F-56D3A3C26D6D: OOS_2 flagged SECURITY.md at "important" and was dropped.

## Affected files

- SECURITY.md: the four passages above.
- skills/review-and-fix/SKILL.md.
- skills/implement/references/step5-review-branches.md.

## Suggested fix(es)

One doc-sync PR updating all six passages. For the cleanup hook, add a dedicated SessionStart paragraph mirroring the sweep-design-logs.sh one, recording the deletion scope: top-level entries only, symlinks skipped, fixed larch-* fnmatch patterns, 7-day age threshold, depth-5 nested-activity check for directories, and the `env -u LARCH_TEST_TMP_ROOT` guard.

## Open questions

- Should ordinal phrases like "the second SessionStart hook" be dropped from SECURITY.md entirely per .claude/rules/drift-prone-prose-in-docs.md, replacing them with hook names only?

## Test plan
(no test plan section in plan-file)
