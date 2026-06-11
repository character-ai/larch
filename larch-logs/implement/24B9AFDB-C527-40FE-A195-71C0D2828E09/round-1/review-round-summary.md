# Review Round 1

- Mode: `diff`
- 4 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: prose blocker fallback drops blockers from successful sources
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `prose_open_blockers` can return no blockers when one source fails. Body, comments, or body JSON failures can discard blockers parsed from the other successful source. Admission can then pass a blocked issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Treat body and comments fetches independently; use empty body or [] on single-source failure; add partial-failure pytest cases
  - From cursor-specialist-correctness-output.txt: Wrap body JSON parse fail-open (empty string) so comment parsing still proceeds
  - From codex-specialist-correctness-output.txt: Treat body and comments failures independently; keep refs from sources that parsed successfully
  - From cursor-specialist-edge-cases-output.txt: On comments failure treat comments as [] and still parse the issue body
  - From codex-specialist-edge-cases-output.txt: Parse body and comments independently; skip only the failed source and preserve blockers found from successful sources.
  - From cursor-specialist-testing-output.txt: On body read failure use empty body and still fetch comments; on comments failure use [] and still parse body; add pytest for partial fetch failure


### FINDING_3: missing issue-state empty-repo subprocess coverage
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The plan-required regression test for `issue state` when repo resolution is empty is missing. A regression that adds `--repo` incorrectly could ship without CI coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add test mirroring test_issue_info_empty_resolution_omits_repo for issue state CLI
  - From cursor-specialist-testing-output.txt: Add test_issue_state_empty_resolution_omits_repo mirroring test_issue_info_empty_resolution_omits_repo


### FINDING_4: issue context help and usage output is hidden by quiet routing
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt, dyn-output-routing-output.txt
- **Severity**: latent
- **Concern**: `issue_context_main` initializes quiet logging before parsing help and validation paths. `--help` and usage errors can write to the quiet log instead of caller-visible stdout or stderr.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Move help/validation before quiet_init or write usage to saved fd3/fd4 while keeping success KV through emit_kv
  - From codex-specialist-testing-output.txt: Parse context args before quiet_init for help and validation-only exits, or route usage to the saved stream after quiet init; add subprocess tests for help and usage output.
  - From dyn-output-routing-output.txt: Parse argv first and handle `--help` / validation exits before `quiet_init`, matching `clarify.py` and the old bash script. For any diagnostics that must run after `quiet_init`, write to saved FD 4 via `os.write(4, ...)` (same pattern as `logging_util.BreadcrumbWriter`), not `print()` to stdout/stderr.


### FINDING_5: missing issue context runtime ShipError test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: There is no plan-required test that `issue context` exits 1 on runtime `ShipError` without emitting a success KV envelope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add monkeypatch or subprocess test where issue_context raises and assert exit 1 with no success KV envelope


