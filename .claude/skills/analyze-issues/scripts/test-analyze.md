# test-analyze.sh

Purpose: regression harness for `.claude/skills/analyze-issues/scripts/analyze.py` behavioral output.

Primary callers: `make test-analyze`, and hand-run via `bash .claude/skills/analyze-issues/scripts/test-analyze.sh`.

Invariants: the assertion list mirrors the `test-fixture.json` row-to-code-path coverage matrix. The fixture pins Tracking/umbrella detection, `[OOS]` prefix stripping, Bug fix categorization, Documentation/contract drift categorization, Hardening/validation/security categorization, duplicate-title waste detection, `[STALLED]` waste detection, reviewer attribution parsing, vote-tally parsing, and the longest-first `codex`/`code` alternation. If `analyze.py` semantics change for any covered branch, update the fixture and assertions in the same PR.

Makefile wiring: `test-analyze` invokes this harness directly and is included in `test-harnesses-5`.

Edit-in-sync: when adding a new branch in `categorize`, `wasteful_findings`, or `reviewer_effectiveness`, extend `test-fixture.json` with one issue exercising it and add a stable-substring assertion in `test-analyze.sh`.
