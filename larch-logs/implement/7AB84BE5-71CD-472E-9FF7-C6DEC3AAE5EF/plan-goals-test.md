## Goal
Scaffold private dev skill /release that promotes larch GitHub releases from pre-release to latest and then runs /upgrade-larch

## Implementation Plan

Goal: Scaffold .claude/skills/release/SKILL.md in the larch3 consumer repo — a private dev skill that (1) finds the latest larch release on GitHub, (2) promotes it from pre-release to latest, and (3) runs /upgrade-larch.

### Files to create
- `.claude/skills/release/SKILL.md` (via render-skill-md.sh)
- `.claude/skills/release/scripts/.gitkeep` (auto-created by renderer)

### Steps

1. Run render-skill-md.sh with:
   - `--name "release"`
   - `--description "1. finds the latest larch release in https://github.com/character-ai/larch/releases; 2. Edits it to clear \"pre-release\" and set \"latest release\" attribute; 3. runs /upgrade-larch.  NOTE: This is a larch repo private skill, not plugin exported."`
   - `--target-dir "/Users/zhupanov/larch3/.claude/skills/release/"`
   - `--local-token "/Users/zhupanov/larch3"`
   - `--plugin-token "/Users/zhupanov/.claude/plugins/cache/larch-local/larch/27.6.12"`
   - `--multi-step false`
   - `--feature-spec-file "/tmp/create-skill-raw-desc-release.txt"`

2. Run post-scaffold-hints.sh to get hints for the consumer-mode skill:
   - `--target-dir ".claude/skills/release/"` `--plugin false`
   - Execute every hint verbatim

3. Run /relevant-checks to validate the scaffold

### Edge cases
- The feature-spec-file path must exist (it was created at Step 1.4 of create-skill)
- The target-dir leaf must not already exist (render-skill-md.sh fails on collision)
- consumer mode: no plugin catalog row, no docs/configuration-and-permissions.md Strict-permissions entry


## Test plan
- render-skill-md.sh exits 0 with `RENDERED=<path>` on stdout
- SKILL.md contains correct frontmatter name/description
- /relevant-checks passes
