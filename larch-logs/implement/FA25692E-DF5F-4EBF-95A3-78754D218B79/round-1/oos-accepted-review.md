### FINDING_20: [OUT_OF_SCOPE] architecture: scripts/launch-codex-implement.sh:380
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Launcher always exits 0 regardless of LAUNCHER_EXIT. Shell callers that only check $? think implement succeeded when emit_kv reports failure. Pre-existing; address in a separate launcher-exit-code issue.
- **Suggested revision**: Address the concern above.


### FINDING_21: [OUT_OF_SCOPE] correctness: scripts/parse-codex-usage.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Omitting reasoning_output_tokens from OUTPUT bucket. Reasoning-heavy runs understate output/cost vs actual Codex billing. Follow-up issue per plan out-of-scope note.
- **Suggested revision**: Address the concern above.


