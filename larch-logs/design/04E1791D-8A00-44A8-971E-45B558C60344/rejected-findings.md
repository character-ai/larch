### [Plan Review] FINDING_1

### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/agents.py:4268-4276
- **Concern**: Item 7 omits `_review_emit_launcher_result` stderr_sink threading. Scenario: Plan says pass `args.stderr_sink` at call sites but never adds a `stderr_sink` parameter or forwards it inside `_review_emit_launcher_result`, which still calls `_review_failure_source(output)` without sink; early auth/preflight review exits skip retry/NS-retry `.failure-diag` and sink candidates
- **Proposed resolution**: Add `stderr_sink: str = ""` to `_review_emit_launcher_result`, delegate through `_review_failure_source(output, sink=stderr_sink)` after resolver alignment, and pass `args.stderr_sink` at all six call sites (lines 4352, 4361, 4431, 4561, 4577, 4633)




### [Plan Review] FINDING_2

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/collect_results.py:788-810
- **Concern**: Phase-derived stderr-tail expansion omits per-candidate retry/NS-retry ordering. Scenario: For a *-phase3.txt reviewer, the loop still prefers {candidate}.launch-stderr before any {stem}-retry.txt.stderr-tail / {stem}-ns-retry.txt.stderr-tail derived from phase2/base; a rendered launch-stderr can mask the phase2-ns-retry tail the issue targets
- **Proposed resolution**: In each collector_stderr_tail_candidates iteration, check derived retry then NS-retry stderr-tail before .launch-stderr; mirror primary-base precedence; pin order in test_collect_results.py




### [Plan Review] FINDING_3

### FINDING_3:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/agents.py:1806-1829,4866-4879; python/implement_dispatch.py:1175-1200
- **Concern**: Implement failure resolver can still mask the real sidecar. Scenario: The proposed `_append_implement_launch_failure` resolver call passes `sink=str(sidecar)`, but `run_external_agent` has already created a generic `.failure-diag` and `.stderr-tail`; the resolver prefers that file over `sink`, and the tail is not regenerated. Codex implement stderr lives at `tmpdir/codex-impl.log`, separate from the transcript path, so item 7/8 diagnostics can still omit the real launcher stderr.
- **Proposed resolution**: Compose or resolve implement failure diagnostics with the sidecar before selecting the source, and regenerate the stderr tail from that selected source when the existing tail came from the generic diag. Keep this limited to `_append_implement_launch_failure` or the implement launcher call path.




### [Plan Review] FINDING_4

### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/agents.py:4017-4028
- **Concern**: python/agents.py:4268-4280. Scenario: Item 7 wires resolver parity into `_review_failure_source` and says to pass `stderr_sink` at `_review_emit_launcher_result` call sites, but the plan never updates `_review_emit_launcher_result` to accept/forward `stderr_sink`, and that path never calls `_compose_failure_diag` before classification
- **Proposed resolution**: On brainstorm/preflight failures `_review_write_failure_sink` can populate `stderr_sink`, while `_review_emit_launcher_result` still classifies from `_review_failure_source(output)` without `sink`; `LAUNCHER_FAILURE_*` KV can disagree with `_review_append_launch_failure` logging and miss retry/NS-retry `.failure-diag` Add `stderr_sink: str = ""` to `_review_emit_launcher_result`, call `_compose_failure_diag(output, sink=stderr_sink)` before resolving the source, delegate to `resolve_failure_diagnostic_source`, and pass `args.stderr_sink` at all six call sites (lines 4352, 4361, 4431, 4561, 4577, 4633); cover sink + retry/NS-retry preference in `python/test_agents.py`




### [Plan Review] FINDING_5

### FINDING_5:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/collect_results.py:788-810
- **Concern**: Phase-derived retry versus NS-retry stderr-tail precedence is unspecified. Scenario: The plan extends `resolve_collector_stderr_tail_file` with per-derived-candidate retry and NS-retry tails but never states that retry beats NS-retry the way the primary path does (`python/collect_results.py:790-795`). An implementer can pick the opposite order and surface stale NS-retry diagnostics for phase2 or base outputs.
- **Proposed resolution**: State explicitly that for every derived candidate stem, `*-retry.txt.stderr-tail` is checked before `*-ns-retry.txt.stderr-tail`, mirroring the existing primary priority; add a paired test when both derived tails exist.




