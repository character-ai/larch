## Acceptance

- `/design` generates the architecture diagram only after Gate C **Approve** (new Step 5b.5, between Step 5b and Step 5c). It is never generated before Gate C; **Discuss further** / **Re-run review panel** loops do not generate it.
- `/design` no longer emits the diagram body to chat: `design-step3b-sanitize.sh` prints no `---LARCH-DIAGRAM-*---` markers, and `SKILL.md` carries no re-emit instruction.
- The architecture diagram still lands in the tracking-issue `larch:diagrams` comment via Step 5c. `DIAGRAM_REQUIRED=false` writes `architecture-diagram.skipped` and Step 5c clears stale Architecture content.
- Diagram body artifacts and diagram-generation/sanitizer failure captures are excluded from committed design run logs; `/implement` no longer copies `code-flow-diagram.failure.log` into `larch-logs/implement/<RUN_ID>/`.
- `/implement` diagram routing is unchanged: still upserted to the tracking issue and embedded in the PR body; never printed to chat.
- Step 5c and `design publish` fail closed when `.completed/step-5b.5` is absent (parallel to the existing `step-5b` guard); publish `--clear-architecture` fires only when `architecture-diagram.skipped` exists.
- Pause/resume reaches Step 5b.5 between Step 5b and Step 5c; a pause before Gate C never resumes into diagram generation.
- `make lint`, `make py-lint`, and `make py-test` pass, including the new `python/test_design_diagram_log.py` and the updated structure, anti-halt, step-7a, pause, publish, and log-publish harnesses.

diff_lines: 675
