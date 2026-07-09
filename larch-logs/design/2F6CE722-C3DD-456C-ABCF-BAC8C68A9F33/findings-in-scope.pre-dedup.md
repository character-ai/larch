### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/git/pr.py:454-469
- **Concern**: body_update_main gates before the body-file existence check. Scenario: When `--body-file` is missing, a gate-relevant tmpdir will return needs-user instead of the existing exit-2 usage error, so an operator typo is masked and the "usage errors stay 2 when no mutation would occur" contract breaks
- **Proposed resolution**: Preflight `args.body_file` before the new gate, or move the gate behind the helper's missing-file check



