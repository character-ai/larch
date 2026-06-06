### FINDING_11: [OUT_OF_SCOPE] Research lanes pass full prompt via inline --prompt CLI arg
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `skills/research/references/research-phase.md:150-156` passes the full prompt via `--prompt` CLI substitution. Very long `RESEARCH_QUESTION` risks `ARG_MAX` / E2BIG; crafted question text also preserves a shell-quoting injection surface at orchestration time. Validation-phase already uses `--prompt-file`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Use --prompt-file with orchestrator-written tmp file like validation-phase.
  - From cursor-specialist-security-output.txt: Document --prompt-file via a pre-written tmpdir file (as validation-phase does) instead of inline --prompt substitution.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_20: [OUT_OF_SCOPE] dialectic-execution.md stale Codex judge launch reference
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `skills/design/references/dialectic-execution.md` still references `run-external-agent` for the Codex judge while `dialectic-protocol.md` uses the launcher, risking stale operator instructions during design sessions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Align dialectic-execution.md with dialectic-protocol.md launcher.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_23: [OUT_OF_SCOPE] Pre-existing empty-output retry loop duplicates parse_retry_meta
- **Reviewer(s)**: dyn-retry-path-parity-output.txt
- **Severity**: latent
- **Concern**: The empty-output retry main loop (~962–1157) inlines full `.meta` parsing instead of calling `parse_retry_meta` (504–546). This predates the branch but grew with new `OUTER_LAUNCHER_*` fields duplicated in both places, increasing maintenance burden.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-retry-path-parity-output.txt: Address the concern above.

Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_8: [OUT_OF_SCOPE] SECURITY.md outer-retry docs omit launch-codex-exec.sh
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `SECURITY.md:188` outer-launcher retry documentation still mentions only `launch-review.sh`, not `launch-codex-exec.sh`, so security readers may underestimate which retry replay paths exist.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Update the outer-retry paragraph to include launch-codex-exec.sh metadata contract.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_9: [OUT_OF_SCOPE] run-external-agent.sh still bypasses shared Codex auth
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-cleanup-lifecycle-output.txt, dyn-retry-path-parity-output.txt
- **Severity**: latent
- **Concern**: `run-external-agent.sh` direct `codex exec` paths remain unwired for shared `external_prepare_codex_auth` / env-key preference by explicit plan OOS. Callers bypassing `launch-codex-exec.sh` (and the linter) can still skip `OPENAI_API_KEY` handling; deferred follow-up sweep per OOS #3475.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Continue the planned follow-up sweep noted in the OOS issue.
  - From cursor-specialist-testing-output.txt: Follow-up sweep wiring external_prepare_codex_auth at remaining call sites.
  - From cursor-specialist-edge-cases-output.txt: Follow-up sweep or wrapper-level auth hook as noted in OOS #3475.
  - From cursor-specialist-plan-fidelity-output.txt: Follow-up sweep per OOS issue; explicitly out of plan scope.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

