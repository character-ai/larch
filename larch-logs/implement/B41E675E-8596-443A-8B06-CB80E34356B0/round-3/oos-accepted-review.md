### FINDING_1: [OUT_OF_SCOPE] Document run-external-agent stderr-only progress contract
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `run-external-agent.sh` now routes default-mode progress, timeout, completion, and diagnostic chatter to stderr so callers can redirect wrapper stdout to JSONL event files safely. The sibling `run-external-agent.md` contract does not document that stream split, which can mislead callers and allow future stdout regressions that corrupt `*.events.jsonl`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_14: [OUT_OF_SCOPE] Raw scout manifests remain allowlisted
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `scripts/larch-log.sh` still allowlists `scout-round*-manifest.json.raw`, which can contain full dynamic-archetype `prompt_body` text. The reviewer marked this as pre-existing and not introduced by the branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_15: [OUT_OF_SCOPE] Negotiation sidecar reuse could become sensitive if exclusions broaden
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `scripts/run-negotiation-round.sh` reuses one `${OUTPUT_FILE%.txt}.sidecar` for Codex stderr and telemetry parse append. This is safe while `*.sidecar` remains excluded, but a future allowlist broadening would make the pre-existing pattern higher impact.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_7: [OUT_OF_SCOPE] run-negotiation-round path resolution differs under symlinks
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/run-negotiation-round.sh` computes `SCRIPT_DIR` without `pwd -P` while `PLUGIN_ROOT` uses `pwd -P`, so symlinked script paths can resolve the script directory and plugin root differently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_8: [OUT_OF_SCOPE] Document telemetry sidecar exclusion explicitly
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/larch-log.md` relies on the generic `*.sidecar` exclusion rather than explicitly mentioning `*.telemetry.sidecar`, so operators may not understand why parse spill files are absent from committed logs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_9: [OUT_OF_SCOPE] Empty --issue value reports less specific error
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `scripts/get-issue-state.sh` reports `ERROR=--issue is required` for `--issue ""` instead of `ERROR=--issue requires a value`; behavior remains safe, but message consistency differs from the new guard paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


