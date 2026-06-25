# Review Round 1

- Mode: `diff`
- 1 accepted, 3 rejected (0 neutral)

## Accepted Findings

### FINDING_3: `codex-round1-adherence` audit scan false-fails normal round 2+ Codex specialist manifests
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, codex-generalist-output.txt
- **Severity**: important
- **Concern**: Restored `codex-round1-adherence` in `python/audit_runs.py` (~150–155) treats any Codex manifest row in round 2+ as a violation. Normal multi-round `/implement` runs with Codex still emit `codex-specialist-*` and dynamic Codex rows when Codex is available, so otherwise-correct runs fail audit (`rounds_with_codex > 0`) even though only generic Codex reviewers were removed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Scope scan to generic slots only (generalist/codex-plan-generic), or fail those slots in any round; allow specialist Codex rows.
  - From codex-specialist-correctness-output.txt: Parse only the legacy generic slot names, or rebaseline the scan to the new invariant.
  - From cursor-specialist-edge-cases-output.txt: Align scan with dispatch: either restore round gating/generic-row topology or keep the #5321 generic-only round-3+ scan instead of any-Codex round-2+.
  - From codex-specialist-edge-cases-output.txt: Restrict the check to generic slot names or output basenames and leave specialist/dynamic Codex rows allowed.
  - From cursor-specialist-testing-output.txt: Restore structured generic-only enforcement (forbid generalist/codex-plan-generic, allow specialist/dynamic Codex) and reinstate the removed audit fixture tests.
  - From codex-specialist-testing-output.txt: Match only the removed generic slot names or update the panel generator if all Codex reviewers were meant to disappear.
  - From codex-generalist-output.txt: Restore the scan to reject only generic Codex slots or outputs, such as `generalist`, `codex-plan-generic`, `codex-generalist-output.txt`, and `codex-plan-generic-output.txt`, and update `.claude/skills/audit-runs/scans-implement.tsv:8` to match.


