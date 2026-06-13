## Decision 1: All check-reviewers.sh callsites are in scope
- **Question**: What consumers of check-reviewers.sh need retargeting?
- **Resolution**: session_env.py (subprocess → direct Python call), agents.py _external_health_gate (subprocess → direct call), lib-external-launcher-common.sh (6 callsites → cli.py agent check-reviewers), skills/status/scripts/status.sh, lint_codex_exec_auth.py allowlist entry removed.
- **Source**: codebase

## Decision 2: run-negotiation-round.sh callsites
- **Question**: What consumers of run-negotiation-round.sh need retargeting?
- **Resolution**: skills/shared/external-reviewers.md bash blocks → python3 cli.py agent run-negotiation-round; skills/research/references/validation-phase.md and docs prose updated.
- **Source**: codebase

## Decision 3: Stamp-file TTL cache mechanism
- **Question**: Should the Python port replicate the bash filesystem-based stamp cache?
- **Resolution**: Yes. Python uses the same /tmp/larch-<tool>-present-<user>.stamp files with the same TTL/negative-TTL semantics.
- **Source**: codebase

## Decision 4: test_agents.py stub migration
- **Question**: How do tests for _external_health_gate change after the port?
- **Resolution**: Tests that stub check-reviewers.sh switch to mocking the Python check_reviewers function directly. Bash harnesses (test-check-reviewers.sh, test-run-negotiation-round.sh) retired.
- **Source**: test_agents.py:696, 734, 751, 776
