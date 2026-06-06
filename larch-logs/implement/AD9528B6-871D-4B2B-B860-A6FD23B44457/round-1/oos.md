### FINDING_10: risk-integration: scripts/test-design-log-publish.md:9-12
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Sibling harness documentation still describes only suffix deny-list coverage. Contributors may miss that plan-review transcript/diagnostic exclusions are regression-pinned in the happy-path case. Update test-design-log-publish.md coverage bullets to document #3534 transcript/sidecar/collector-failure exclusions and canonical findings.md/voting-tally.md preservation.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_13: [OUT_OF_SCOPE] architecture: scripts/lib-design-round-artifacts.sh:8
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] dyn-*-output.txt exclude pattern does not match real dynamic output basenames. Pre-existing dead pattern; dynamic outputs are excluded via cursor-plan-* and codex-primary-plan-* patterns instead. Consider replacing dyn-*-output.txt with explicit cursor-plan-dyn-* and codex-primary-plan-dyn-* patterns in a follow-up.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_16: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **security** `scripts/design-log-publish.sh:294-327` — Top-level `design_artifact_excluded()` still default-allows `render-plan-*.prompt` / `render-plan-codex-*.prompt` / `render-plan-cursor-*.prompt`. Committed design logs already contain full panel prompts (plan text, feature context, reviewer instructions) at paths like `larch-logs/design/*/render-plan-cursor-arch.prompt`. This predates #3534; the new `claude-plan-*.prompt` arm excludes only the Claude generic fallback, not Codex/Cursor rendered prompts. **Suggested fix:** follow-up issue to deny `render-plan-*.prompt` (and optionally `render-plan-codex-*.prompt` / `render-plan-cursor-*.prompt`) at top level, mirroring the transcript exclusion philosophy.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_17: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **security** `scripts/design-log-publish.sh:294-327` — Top-level `cursor-plan-voter-prompt.txt` (and similar `*-voter-prompt.txt`) remain publishable; round-N staging excludes `*-vote-prompt.txt` but the top-level gate does not. Committed logs include voter prompts with ballot context. Pre-existing gap, not introduced by this diff. **Suggested fix:** add a top-level deny pattern for `*-voter-prompt.txt` / `*-vote-prompt.txt` if voter prompts should match round-N policy.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_18: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 3. **security** `scripts/design-log-publish.sh:308-325` — `claude-plan-assessor-round-<N>.txt` (and `.json` sidecars) do not match `claude-plan-*-output*.txt` and remain publishable at top level when present. The implementation plan explicitly deferred assessor outputs. Pre-existing / intentional deferral. **Suggested fix:** separate follow-up if assessor transcripts should be treated like other raw LLM outputs.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_22: [OUT_OF_SCOPE] security: scripts/design-log-publish.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] render-plan-*.prompt files not excluded by this change. Pre-existing prompt publication in committed design logs continues unchanged. Follow-up issue if prompt exclusion is desired.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_23: [OUT_OF_SCOPE] architecture: scripts/lib-design-round-artifacts.sh:8
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] dyn-*-output.txt exclude pattern matches no producer. Dead pattern only; no current leakage. Remove or replace with real dynamic basename patterns when touching allowlist.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_24: [OUT_OF_SCOPE] security: larch-logs/design/
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] aggregator-output-phase2.txt and codex-vote-output-phase2.txt still publish. Pre-existing phased non-plan-review artifacts; out of #3534 transcript-family scope. Track separately if vote/aggregator phased outputs should be gated.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_30: [OUT_OF_SCOPE] **Pre-existing dead round-N pattern:** `scripts/lib-design-round-artifacts.sh:242` still lists `dyn-*-output.txt`, but real dynamic outputs are `cursor-plan-dyn-*-output.txt` and `codex-primary-plan-dyn-*-output.txt` (`dispatch-plan-review-panel.sh:234-243`). This branch only repairs the sibling dead `codex-plan-*` pattern; behavior is unchanged because the round-N catch-all still excludes real names via the `cursor-plan-*` / `codex-primary-plan-*` arms.
- **Reviewer**: dyn-deny-completeness-output.txt
- **Concern**: - **Pre-existing dead round-N pattern:** `scripts/lib-design-round-artifacts.sh:242` still lists `dyn-*-output.txt`, but real dynamic outputs are `cursor-plan-dyn-*-output.txt` and `codex-primary-plan-dyn-*-output.txt` (`dispatch-plan-review-panel.sh:234-243`). This branch only repairs the sibling dead `codex-plan-*` pattern; behavior is unchanged because the round-N catch-all still excludes real names via the `cursor-plan-*` / `codex-primary-plan-*` arms.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_31: [OUT_OF_SCOPE] **Cursor/Codex `.stderr` / `.stderr-tail` omission is consistent with producers:** `launch-review.sh` routes launcher stderr to `.sidecar` / optional `--stderr-sink`, not `${OUTPUT}.stderr` / `.stderr-tail`; only `launch-claude-subprocess.sh` writes those suffixes (`scripts/launch-claude-subprocess.sh:205-231`). The branch correctly limits Claude-only `.stderr*` sidecars.
- **Reviewer**: dyn-deny-completeness-output.txt
- **Concern**: - **Cursor/Codex `.stderr` / `.stderr-tail` omission is consistent with producers:** `launch-review.sh` routes launcher stderr to `.sidecar` / optional `--stderr-sink`, not `${OUTPUT}.stderr` / `.stderr-tail`; only `launch-claude-subprocess.sh` writes those suffixes (`scripts/launch-claude-subprocess.sh:205-231`). The branch correctly limits Claude-only `.stderr*` sidecars.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_32: [OUT_OF_SCOPE] **Collector failure-log slot prefixes match production:** `plan-review-loop.sh:1076-1080` derives `${slot}-collector.failure.log` from manifest slots (`cursor-plan-*`, `codex-plan-*`, `dyn-cursor-plan-*`, `dyn-codex-plan-*`, or `unknown-slot` at line 859). The deny list covers those families; a dedicated `claude-plan-*-collector.failure.log` arm is unnecessary for the plan-review panel because Claude generic failures map to `unknown-slot`.
- **Reviewer**: dyn-deny-completeness-output.txt
- **Concern**: - **Collector failure-log slot prefixes match production:** `plan-review-loop.sh:1076-1080` derives `${slot}-collector.failure.log` from manifest slots (`cursor-plan-*`, `codex-plan-*`, `dyn-cursor-plan-*`, `dyn-codex-plan-*`, or `unknown-slot` at line 859). The deny list covers those families; a dedicated `claude-plan-*-collector.failure.log` arm is unnecessary for the plan-review panel because Claude generic failures map to `unknown-slot`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_36: [OUT_OF_SCOPE] architecture
- **Reviewer**: dyn-doc-code-parity-output.txt
- **Concern**: - **architecture** `scripts/lib-design-round-artifacts.md:23` — The documented include basename list still omits `findings-in-scope.pre-dedup.md` and `plan-review-scope-anchor.txt`, which are included in `scripts/lib-design-round-artifacts.sh:17-23`. Pre-existing doc drift, not introduced by this branch.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_37: [OUT_OF_SCOPE] architecture
- **Reviewer**: dyn-doc-code-parity-output.txt
- **Concern**: - **architecture** `scripts/lib-design-round-artifacts.md:27`, `scripts/lib-design-round-artifacts.sh:8` — The `dyn-*-output.txt` exclude pattern remains documented and coded but does not match real `/design` plan-review producers (`cursor-plan-dyn-*-output.txt`, `codex-primary-plan-dyn-*-output.txt`). The branch fixed the fictional `codex-plan-*` name but left this legacy pattern; behavior is unchanged because dynamic outputs are covered by the cursor/codex-primary patterns.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_4: [OUT_OF_SCOPE] code-quality: scripts/design-log-publish.sh:322
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] claude-plan-*.prompt is excluded but render-plan-cursor-*.prompt and render-plan-codex-dyn-*.prompt are not. Full static/dynamic reviewer prompts may still flush to larch-logs/design/ at top level. Pre-existing; outside #3534 plan-review output scope. Extend deny patterns to render-plan-*.prompt if prompt publication should match transcript exclusion policy.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_5: [OUT_OF_SCOPE] code-quality: scripts/design-log-publish.sh:294-327
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Sketch-phase outputs (cursor-sketch-*-output.txt) are outside new *-plan-* deny patterns. Sketch raw transcripts may still commit at top level. Pre-existing; outside #3534 scope. Add sketch transcript deny arms if design logs should exclude all raw external reviewer outputs.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_7: [OUT_OF_SCOPE] correctness: scripts/lib-design-round-artifacts.sh:8
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] dyn-*-output.txt exclude pattern does not match real dynamic output basenames (cursor-plan-dyn-*, codex-primary-plan-dyn-*). Dead pattern misdocuments behavior; real dynamic transcripts rely on cursor/codex-primary explicit arms or round-N catch-all exclusion only. Replace dyn-*-output.txt with cursor-plan-dyn-*-output.txt and codex-primary-plan-dyn-*-output.txt in lib + .md + tests, or drop the dead arm.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_8: [OUT_OF_SCOPE] security: scripts/design-log-publish.sh:294-327
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] render-plan-*.prompt top-level prompts remain publishable (pre-existing). Full external reviewer prompts with plan content can still flush to committed design logs. Out of scope for #3534; consider a follow-up deny arm if prompt publication is undesired.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

