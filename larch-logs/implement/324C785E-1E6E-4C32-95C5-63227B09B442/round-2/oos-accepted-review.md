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


