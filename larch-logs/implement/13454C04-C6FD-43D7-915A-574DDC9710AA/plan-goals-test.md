## Goal
Use Pacific-time (PDT/PST) timestamps instead of UTC in audit-runs report title and frontmatter

## Implementation Plan
Update .claude/skills/audit-runs/SKILL.md and test-audit-runs.sh to use Pacific-time (PDT/PST) timestamps.


### Goals
- Change ISO-timestamp definition in `### Title Format` from UTC (`Z` suffix) to Pacific time with explicit UTC offset (`-07:00` PDT / `-08:00` PST)
- Update `audit_timestamp` frontmatter field spec to use same Pacific-time convention
- Update test-audit-runs.sh to use PDT format `2026-05-20T12:30-07:00` instead of UTC `2026-05-20T19:30Z`
- Document that `audit_timestamp` is NOT used in the "since last audit" comparison path

### Files to modify
1. `.claude/skills/audit-runs/SKILL.md` — Title Format section (line 146)
2. `.claude/skills/audit-runs/scripts/test-audit-runs.sh` — all hardcoded UTC timestamps

### Key decisions
- Prefer offset notation (`-07:00`/`-08:00`) over abbreviation (`PDT`/`PST`) per the issue — DST boundaries make abbreviations ambiguous
- `audit_timestamp` is for the report title/frontmatter only; "since last audit" uses `audited_pr_range.last.mergedAt` (UTC from GitHub API) — no timezone conversion needed


## Test plan
- `bash .claude/skills/audit-runs/scripts/test-audit-runs.sh` must pass
- `/relevant-checks` (pre-commit on modified files + agent-lint)
