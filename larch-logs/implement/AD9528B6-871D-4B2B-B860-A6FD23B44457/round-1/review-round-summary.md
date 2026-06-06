# Review Round 1

- Mode: `diff`
- 4 accepted, 16 rejected (12 exonerated)

## Accepted Findings

### FINDING_11: risk-integration: scripts/test-design-log-publish.sh:481-492
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Cursor .meta sidecar exclusion is implemented but not fixture-tested. A regression in the cursor-plan-*-output*.txt.meta case arm would not fail the harness. Add cursor-plan-arch-output.txt.meta to fixtures and the denied-basename loop.
- **Suggested revision**: Address the concern above.


### FINDING_12: risk-integration: scripts/test-design-log-publish.sh:473-479
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Cursor phased waterfall transcript basenames are not in the deny-loop fixtures. A Cursor-only typo in phased glob handling could leave cursor-plan-arch-output-phase2.txt publishable while Codex phased fixtures still pass. Add cursor-plan-arch-output-phase2.txt to fixtures and the denied loop.
- **Suggested revision**: Address the concern above.


### FINDING_33: **architecture** `scripts/design-log-publish.md:38-41`, `scripts/design-log-publish.sh:316-317`, `SECURITY.md:49-53` — The updated docs state that codex `.json` sidecars have no producers and are intentionally omitted from `design_artifact_excluded()`, but `launch-review.sh` copies every non-empty reviewer `OUTPUT` to `${OUTPUT}.json` for both `cursor` and `codex` (`scripts/launch-review.sh:1149-1150`), including phased names such as `codex-primary-plan-arch-output-phase2.txt.json`. The code excludes only `cursor-plan-*-output*.txt.json` (`scripts/design-log-publish.sh:313`); codex-primary `.json` files are not denied, so they still pass the gate and are published via the `*-output*.json` trim branch (`scripts/design-log-publish.sh:360-364`). Committed design logs already contain many `codex-primary-plan-*-output-phase2.txt.json` artifacts under `larch-logs/design/`, so the new documentation overstates the publication boundary and leaves a real leak after transcript exclusion. **Suggested fix:** Add `codex-primary-plan-*-output*.txt.json` to the plan-review deny branch in `design_artifact_excluded()`, pin a phased fixture in `scripts/test-design-log-publish.sh`, and align `scripts/design-log-publish.md` and `SECURITY.md` to list codex `.json` among excluded producer-backed sidecars (or document an explicit, tested exception if strip-and-publish is intended).
- **Reviewer**: dyn-doc-code-parity-output.txt
- **Concern**: - **architecture** `scripts/design-log-publish.md:38-41`, `scripts/design-log-publish.sh:316-317`, `SECURITY.md:49-53` — The updated docs state that codex `.json` sidecars have no producers and are intentionally omitted from `design_artifact_excluded()`, but `launch-review.sh` copies every non-empty reviewer `OUTPUT` to `${OUTPUT}.json` for both `cursor` and `codex` (`scripts/launch-review.sh:1149-1150`), including phased names such as `codex-primary-plan-arch-output-phase2.txt.json`. The code excludes only `cursor-plan-*-output*.txt.json` (`scripts/design-log-publish.sh:313`); codex-primary `.json` files are not denied, so they still pass the gate and are published via the `*-output*.json` trim branch (`scripts/design-log-publish.sh:360-364`). Committed design logs already contain many `codex-primary-plan-*-output-phase2.txt.json` artifacts under `larch-logs/design/`, so the new documentation overstates the publication boundary and leaves a real leak after transcript exclusion. **Suggested fix:** Add `codex-primary-plan-*-output*.txt.json` to the plan-review deny branch in `design_artifact_excluded()`, pin a phased fixture in `scripts/test-design-log-publish.sh`, and align `scripts/design-log-publish.md` and `SECURITY.md` to list codex `.json` among excluded producer-backed sidecars (or document an explicit, tested exception if strip-and-publish is intended).
- **Suggested revision**: Address the concern above.


### FINDING_6: correctness: scripts/design-log-publish.sh:313-319
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Cursor/Codex plan-review .stderr-tail sidecars are not denied; only Claude stderr/stderr-tail is excluded. When a Cursor or Codex plan-review slot fails, run-external-agent.sh (via launch-review.sh) writes e.g. cursor-plan-arch-output.txt.stderr-tail; design_artifact_excluded returns false and design-log publish commits redacted stderr tails to larch-logs/design/<run-id>/, partially defeating the raw-output exclusion goal. Add cursor-plan-*-output*.txt.stderr-tail and codex-primary-plan-*-output*.txt.stderr-tail to design_artifact_excluded, add deny-loop fixtures in test-design-log-publish.sh, and sync design-log-publish.md and SECURITY.md.
- **Suggested revision**: Address the concern above.


