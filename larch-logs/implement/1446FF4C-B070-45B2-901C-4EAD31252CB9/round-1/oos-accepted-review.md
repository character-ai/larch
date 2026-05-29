### FINDING_11: [OUT_OF_SCOPE] `SCOUT_LATENCY_MS` reports last tier only
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `SCOUT_LATENCY_MS` is last-tier only. Waterfall latency is under-reported in timing KV output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Sum per-tier ELAPSED or emit per-tier timing keys.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_19: [OUT_OF_SCOPE] `SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_*` env overrides
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `SCOUT_DYNAMIC_ARCHETYPES_LAUNCH_*` env overrides can replace launchers. Malicious or stale env in operator shell could redirect scout launches to arbitrary scripts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Document in SECURITY.md; restrict overrides to harness contexts


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_20: [OUT_OF_SCOPE] no max length on scout `prompt_body` in jq validation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: No max length on scout `prompt_body` in jq validation. Oversized `prompt_body` could bloat dynamic reviewer prompts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Add prompt_body byte/line cap in scout validation


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


