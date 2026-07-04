### FINDING_7:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/design/design_step5b.py:192-285
- **Concern**: [SCOPE-REDUCTION] Prior Bug A retry fix is still wired at the wrong boundary. Scenario: `design_step5b.py` has no Skill-tool boundary, while `finalize-step5.md` states the `/larch:issue` call is prompt-side; making the wrapper re-run `/larch:issue` forces a duplicate lower-level issue pipeline or leaves `NEXT_ACTION=retry-file-and-annotate` unreachable.
- **Proposed resolution**: Keep `design_step5b.py` limited to emitting the retryable status and withholding `.completed/step-5b`; make `skills/design/references/finalize-step5.md` own the one allowed `/larch:issue` retry followed by a second annotate call.
