### OOS_1: agnix-fix may still flag adjacent bash fences on first-run lint
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The plan names agnix-fix for first-run remediation, but the diff adds no suppression there. Adjacent bash fences at `.claude/skills/agnix-fix/SKILL.md:52-68` and `72-97` appear separated only by a one-line breadcrumb gap. `make lint` / pre-commit `lint-consecutive-bash` can exit 1 despite other scoped files being remediated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Run python3 python/cli.py lint consecutive-bash; if flagged, add a justified suppression using the correct placement form for that fence shape.
