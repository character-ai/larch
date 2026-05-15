### REJ_C1: Cursor-Structure (round 1) [code-review/rejected]

**Finding**: `dispatch-panel.sh` emits EXTERNAL_OUTPUT_FILES / CLAUDE_OUTPUT_FILES as IFS-joined space-separated strings via `emit_kv` instead of the original per-path `%q`-quoted format. Concern: paths containing spaces would be ambiguous for downstream consumers splitting on spaces.
**Reason not implemented**: Reviewer output paths are always written under the larch session tmpdir (e.g. ~/.cache/larch/sessions/...) which never contains spaces; the emit_kv space-joined output is functionally equivalent to the original %q encoding for this use case. Changing to a structured encoding would require updating all consumers and is a larger API change beyond this PR's scope.

### REJ_C2: Cursor-Testing (round 1) [code-review/rejected]

**Finding**: `run-negotiation-round.sh` has no Makefile-backed test harness after emit_kv conversion, missing CI coverage.
**Reason not implemented**: Adding a new test harness is out of scope for a mechanical quiet-conversion PR. Would be filed as a follow-up.

### REJ_C3: Cursor-Structure (round 1) [code-review/rejected]

**Finding**: `compose-tally-record.sh` has no dedicated harness for the larch_quiet_init + exec 1>&3 pattern.
**Reason not implemented**: Same as above — new test harness addition is out of scope.

### REJ_C4: Cursor-Structure (round 1) [code-review/rejected]

**Finding**: `.md` contract siblings add "FAILURE_LOG=<path> may appear on stdout" but scripts do not explicitly emit this key.
**Reason not implemented**: The "may" wording is intentionally soft — it documents the LARCH_QUIET_LOG_FILE forward-looking convention. Implementing explicit FAILURE_LOG emission is a follow-up.

### REJ_C5: Cursor-Edge-cases (round 1) [code-review/rejected]

**Finding**: After larch_quiet_init, stderr from launch-review.sh/wait-for-reviewers.sh/launch-claude-subprocess.sh goes to quiet log instead of dispatch-panel.sh's capture file. Diagnostic messages may be harder to find.
**Reason not implemented**: The FAILURE_LOG .md documentation documents the intended fix (emitting the quiet log path on failure). Not a regression in existing passing tests. Proper implementation (emitting FAILURE_LOG + consumer reading it) is a follow-up.

### REJ_C6: Cursor-Edge-cases (round 1) [code-review/rejected]

**Finding**: log-phase.sh EXIT trap only cleans up one temp file; future second EXIT cleanup could be overwritten.
**Reason not implemented**: Only one resource is cleaned up in the current script; the concern is latent and best addressed if/when a second resource is added.

