### OOS_1: [OUT_OF_SCOPE] No offline harness for standalone Step 4 transcript and commit wiring
- **Description**: [OUT_OF_SCOPE] No offline harness for standalone Step 4 transcript and commit wiring. Scenario: Issue #5976 item 3 asked for a dedicated Step 4 regression harness (nested skip, argv, SESSION_UUID mismatch). The plan deliberately omits it and only offers an optional structure pin. Future edits to Step 4 guards can regress without CI signal beyond grep pins.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/review/SKILL.md:111-111
- **Phase**: design



### OOS_2: [OUT_OF_SCOPE] capture-transcript could resolve log-root like commit instead of SKILL-only hoisting
- **Description**: [OUT_OF_SCOPE] capture-transcript could resolve log-root like commit instead of SKILL-only hoisting. Scenario: run-log commit rejects empty roots via _resolve_log_root, but capture-transcript uses Path(args.log_root) directly, so an empty --log-root stages under a cwd-relative review/<RUN_ID>/ tree. Hoisting review_log_root in SKILL.md fixes /review Step 4 only; the same footgun remains for any future caller that omits --log-root.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/report/run_log_flush.py:811-812
- **Phase**: design



