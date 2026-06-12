### OOS_1: [OUT_OF_SCOPE] `SECURITY.md` undercounts emergency Preflight bypasses
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, dyn-architecture-output.txt, dyn-architecture-codex-output.txt
- **Severity**: important
- **Concern**: `SECURITY.md:245` still says emergency bypasses exactly three Preflight gates and does not suppress admission, while current implement docs and `scripts/implement-preflight.sh:214-218` allow `--emergency` to bypass `missing-designed-prefix` admission (four downgrade gates total). An operator can run `/implement --emergency --merge` on an issue without `[DESIGNED]` contrary to the documented security boundary. The paragraph was not fully harmonized with `skills/implement/SKILL.md` in the same edit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Update the paragraph to list four downgrade gates including missing-designed-prefix and clarify that other admission failures still block.
  - From codex-specialist-edge-cases-output.txt: Update SECURITY.md to list four downgrades and clarify that only missing-designed-prefix is bypassable under admission, while other admission blocks still fail closed.
  - From dyn-architecture-codex-output.txt: In a separate cleanup, revise the SECURITY wording to count or enumerate `missing-designed-prefix` consistently with the helper behavior.


