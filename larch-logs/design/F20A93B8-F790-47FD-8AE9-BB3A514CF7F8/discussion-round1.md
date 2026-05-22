## Decision 1: Where to add "show latest design proposal" option
- **Question**: Where exactly should the new option appear?
- **Resolution**: Gate A post-plan re-entry only (re-entered from Gate B(c) or Gate C(b)). Do NOT add to first-time Gate A entry (no plan exists yet) and do NOT add to Gate B or Gate C.
- **Source**: user

## Decision 2: Branch state when /design runs standalone
- **Question**: When Step 1 branch creation is removed, what should /design do about branch state?
- **Resolution**: /design never runs from /implement anymore. /design is fully standalone. It must not create a feature branch and must not require any specific branch state on entry. /implement is a separate command that creates its own feature branch at start and cleans it up after PR merge.
- **Source**: user

## Decision 3: Env-var persistence pattern
- **Question**: Which pattern should fix the env-var-persistence bug?
- **Resolution**: Source a session-env.sh written by session-setup.sh. Pattern: session-setup.sh writes the env file inside SESSION_TMPDIR (sanctioned writer); every subsequent Bash block in SKILL.md begins by sourcing it. Requires a stable handoff path since SESSION_TMPDIR is per-run.
- **Source**: user
