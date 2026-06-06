### FINDING_1: code-quality: scripts/lib-design-round-artifacts.sh:8
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] PR fixes dead codex-plan-*-output.txt exclude arm but leaves dyn-*-output.txt in the same case; no producer emits output basenames starting with dyn-. Real dynamic outputs are cursor-plan-dyn-*-output.txt and codex-primary-plan-dyn-*-output.txt. Maintainers may believe dyn-*-output.txt excludes dynamic reviewer transcripts; it matches zero production basenames (same bug class as the removed codex-plan-* pattern). Harm is low because cursor-plan-* and codex-primary-plan-* patterns cover real files. Remove dyn-*-output.txt from design_round_artifact_included and lib-design-round-artifacts.md, or replace with real producer prefixes and a comment citing dispatch-plan-review-panel.sh.
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: scripts/design-log-publish.sh:308-325
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Plan-review exclusions are a large inline case block in design_artifact_excluded while design_round_artifact_included encodes overlapping rules with different glob strictness; edit-in-sync rule does not cover test-design-log-publish.sh for top-level deny changes. Future producer rename (e.g. new phased suffix) may update one gate or test surface and miss others, reintroducing committed raw transcripts. Extract shared basename patterns to lib-design-round-artifacts.sh or extend edit-in-sync rule to require test-design-log-publish.sh on top-level deny changes.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: scripts/test-design-log-publish.sh:538-577
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] ~35 denied basenames are hardcoded in a for-loop parallel to design_artifact_excluded case arms with no mechanical linkage. Drift between function globs and test fixture list can pass CI while missing a newly added transcript family (prior codex-plan-* fictional fixtures demonstrated this class). Add table-driven unit assertions that call design_artifact_excluded directly; keep one integration publish smoke test.
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] code-quality: scripts/design-log-publish.sh:322
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] claude-plan-*.prompt is excluded but render-plan-cursor-*.prompt and render-plan-codex-dyn-*.prompt are not. Full static/dynamic reviewer prompts may still flush to larch-logs/design/ at top level. Pre-existing; outside #3534 plan-review output scope. Extend deny patterns to render-plan-*.prompt if prompt publication should match transcript exclusion policy.
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] code-quality: scripts/design-log-publish.sh:294-327
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Sketch-phase outputs (cursor-sketch-*-output.txt) are outside new *-plan-* deny patterns. Sketch raw transcripts may still commit at top level. Pre-existing; outside #3534 scope. Add sketch transcript deny arms if design logs should exclude all raw external reviewer outputs.
- **Suggested revision**: Address the concern above.

### FINDING_6: correctness: scripts/design-log-publish.sh:313-319
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Cursor/Codex plan-review .stderr-tail sidecars are not denied; only Claude stderr/stderr-tail is excluded. When a Cursor or Codex plan-review slot fails, run-external-agent.sh (via launch-review.sh) writes e.g. cursor-plan-arch-output.txt.stderr-tail; design_artifact_excluded returns false and design-log publish commits redacted stderr tails to larch-logs/design/<run-id>/, partially defeating the raw-output exclusion goal. Add cursor-plan-*-output*.txt.stderr-tail and codex-primary-plan-*-output*.txt.stderr-tail to design_artifact_excluded, add deny-loop fixtures in test-design-log-publish.sh, and sync design-log-publish.md and SECURITY.md.
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] correctness: scripts/lib-design-round-artifacts.sh:8
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] dyn-*-output.txt exclude pattern does not match real dynamic output basenames (cursor-plan-dyn-*, codex-primary-plan-dyn-*). Dead pattern misdocuments behavior; real dynamic transcripts rely on cursor/codex-primary explicit arms or round-N catch-all exclusion only. Replace dyn-*-output.txt with cursor-plan-dyn-*-output.txt and codex-primary-plan-dyn-*-output.txt in lib + .md + tests, or drop the dead arm.
- **Suggested revision**: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] security: scripts/design-log-publish.sh:294-327
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] render-plan-*.prompt top-level prompts remain publishable (pre-existing). Full external reviewer prompts with plan content can still flush to committed design logs. Out of scope for #3534; consider a follow-up deny arm if prompt publication is undesired.
- **Suggested revision**: Address the concern above.

### FINDING_9: risk-integration: scripts/test-design-log-publish.sh:431-580
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Happy-path publish harness asserts denied basenames but never pins a near-miss publishable basename the plan calls out of scope. A future broadening of claude-plan transcript globs (e.g. claude-plan-*.txt) could exclude claude-plan-assessor-round-N.txt while all current deny-loop assertions still pass. Add claude-plan-assessor-round-1.txt to the fixture tree and assert it is present in the published larch-logs/design/RUNPUB1/ tree after publish.
- **Suggested revision**: Address the concern above.

### FINDING_10: risk-integration: scripts/test-design-log-publish.md:9-12
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Sibling harness documentation still describes only suffix deny-list coverage. Contributors may miss that plan-review transcript/diagnostic exclusions are regression-pinned in the happy-path case. Update test-design-log-publish.md coverage bullets to document #3534 transcript/sidecar/collector-failure exclusions and canonical findings.md/voting-tally.md preservation.
- **Suggested revision**: Address the concern above.

### FINDING_11: risk-integration: scripts/test-design-log-publish.sh:481-492
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Cursor .meta sidecar exclusion is implemented but not fixture-tested. A regression in the cursor-plan-*-output*.txt.meta case arm would not fail the harness. Add cursor-plan-arch-output.txt.meta to fixtures and the denied-basename loop.
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: scripts/test-design-log-publish.sh:473-479
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Cursor phased waterfall transcript basenames are not in the deny-loop fixtures. A Cursor-only typo in phased glob handling could leave cursor-plan-arch-output-phase2.txt publishable while Codex phased fixtures still pass. Add cursor-plan-arch-output-phase2.txt to fixtures and the denied loop.
- **Suggested revision**: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] architecture: scripts/lib-design-round-artifacts.sh:8
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] dyn-*-output.txt exclude pattern does not match real dynamic output basenames. Pre-existing dead pattern; dynamic outputs are excluded via cursor-plan-* and codex-primary-plan-* patterns instead. Consider replacing dyn-*-output.txt with explicit cursor-plan-dyn-* and codex-primary-plan-dyn-* patterns in a follow-up.
- **Suggested revision**: Address the concern above.

### FINDING_14: `eb4ed1782` — Exclude raw plan-review outputs from design-log publish (#3534)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `eb4ed1782` — Exclude raw plan-review outputs from design-log publish (#3534)
- **Suggested revision**: Address the concern above.

### FINDING_15: `ce56735fa` — chore(larch-logs): flush implement run (out of review scope per policy)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `ce56735fa` — chore(larch-logs): flush implement run (out of review scope per policy)
- **Suggested revision**: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **security** `scripts/design-log-publish.sh:294-327` — Top-level `design_artifact_excluded()` still default-allows `render-plan-*.prompt` / `render-plan-codex-*.prompt` / `render-plan-cursor-*.prompt`. Committed design logs already contain full panel prompts (plan text, feature context, reviewer instructions) at paths like `larch-logs/design/*/render-plan-cursor-arch.prompt`. This predates #3534; the new `claude-plan-*.prompt` arm excludes only the Claude generic fallback, not Codex/Cursor rendered prompts. **Suggested fix:** follow-up issue to deny `render-plan-*.prompt` (and optionally `render-plan-codex-*.prompt` / `render-plan-cursor-*.prompt`) at top level, mirroring the transcript exclusion philosophy.
- **Suggested revision**: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **security** `scripts/design-log-publish.sh:294-327` — Top-level `cursor-plan-voter-prompt.txt` (and similar `*-voter-prompt.txt`) remain publishable; round-N staging excludes `*-vote-prompt.txt` but the top-level gate does not. Committed logs include voter prompts with ballot context. Pre-existing gap, not introduced by this diff. **Suggested fix:** add a top-level deny pattern for `*-voter-prompt.txt` / `*-vote-prompt.txt` if voter prompts should match round-N policy.
- **Suggested revision**: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 3. **security** `scripts/design-log-publish.sh:308-325` — `claude-plan-assessor-round-<N>.txt` (and `.json` sidecars) do not match `claude-plan-*-output*.txt` and remain publishable at top level when present. The implementation plan explicitly deferred assessor outputs. Pre-existing / intentional deferral. **Suggested fix:** separate follow-up if assessor transcripts should be treated like other raw LLM outputs.
- **Suggested revision**: Address the concern above.

### FINDING_19: security: SECURITY.md:26-34
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] SECURITY.md documents plan-review exclusions as comprehensive but omits that render-plan-*.prompt files still publish. After merge, operators trust SECURITY.md and believe plan-review prompts are gated; render-plan-cursor/codex prompts with plan and feature text still land in larch-logs/design/<run-id>/ top level. Add explicit carve-out or extend design_artifact_excluded to deny render-plan-*.prompt; document whichever policy is chosen in design-log-publish.md.
- **Suggested revision**: Address the concern above.

### FINDING_20: correctness: scripts/design-log-publish.sh:322
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Collector failure denylist covers unknown-slot-collector.failure.log but not slot-collector.failure.log from empty-slug fallback. plan-review-loop.sh sanitization fallback writes slot-collector.failure.log for empty slot names; file can flush with compose-collector-failure/append-tool-failure content. Deny slot-collector.failure.log or use sole-producer *-collector.failure.log pattern with plan-review-loop.sh comment.
- **Suggested revision**: Address the concern above.

### FINDING_21: code-quality: scripts/test-lib-design-round-artifacts.sh:53-56
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Round-N helper excludes phased plan-review transcripts only via default *) arm; no phased fixtures. Future allowlist edit could accidentally include phased raw transcripts while top-level gate and tests stay correct. Add assert_excluded for *-output-phase2.txt basenames; consider *-output*.txt exclude suffix in lib-design-round-artifacts.sh.
- **Suggested revision**: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] security: scripts/design-log-publish.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] render-plan-*.prompt files not excluded by this change. Pre-existing prompt publication in committed design logs continues unchanged. Follow-up issue if prompt exclusion is desired.
- **Suggested revision**: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] architecture: scripts/lib-design-round-artifacts.sh:8
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] dyn-*-output.txt exclude pattern matches no producer. Dead pattern only; no current leakage. Remove or replace with real dynamic basename patterns when touching allowlist.
- **Suggested revision**: Address the concern above.

### FINDING_24: [OUT_OF_SCOPE] security: larch-logs/design/
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] aggregator-output-phase2.txt and codex-vote-output-phase2.txt still publish. Pre-existing phased non-plan-review artifacts; out of #3534 transcript-family scope. Track separately if vote/aggregator phased outputs should be gated.
- **Suggested revision**: Address the concern above.

### FINDING_25: `eb4ed1782` — Exclude raw plan-review outputs from design-log publish (#3534)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `eb4ed1782` — Exclude raw plan-review outputs from design-log publish (#3534)
- **Suggested revision**: Address the concern above.

### FINDING_26: `ce56735fa` — chore(larch-logs): flush implement run (out of scope per review rules)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `ce56735fa` — chore(larch-logs): flush implement run (out of scope per review rules) Walked the implementation plan requirement-by-requirement against commit `eb4ed1782`. The diff touches all seven planned files and matches the stated intent.
- **Suggested revision**: Address the concern above.

### FINDING_27: **architecture** `scripts/design-log-publish.sh:308-325` — The new deny arms cover reviewer *transcripts* and `claude-plan-*.prompt`, but not the Cursor/Codex plan-review *prompt files* that `dispatch-plan-review-panel.sh` writes at session root (`render-plan-cursor-${archetype}.prompt`, `render-plan-codex-${archetype}.prompt`, and `render-plan-*-dyn-${slug}.prompt`; see `skills/design/scripts/dispatch-plan-review-panel.sh:189-244`). Those files embed the same sensitive material as excluded outputs (feature description, full plan text, dynamic scout bodies via `render-plan-review-prompt.sh:132-146`), and committed design logs already flush them at top level (e.g. `larch-logs/design/*/render-plan-cursor-arch.prompt`). Excluding transcripts while leaving these prompts publishable leaves a large deny-completeness hole relative to the #3534 “findings canonical / raw plan-review excluded” goal, and the updated `SECURITY.md` / `design-log-publish.md` prose overstates coverage. **Suggested fix:** Add producer-backed deny patterns for `render-plan-cursor-*.prompt` and `render-plan-codex-*.prompt` (static + dyn) in `design_artifact_excluded()`, pin them in `scripts/test-design-log-publish.sh`, and document them beside `claude-plan-*.prompt` in `SECURITY.md` and `scripts/design-log-publish.md`.
- **Reviewer**: dyn-deny-completeness-output.txt
- **Concern**: - **architecture** `scripts/design-log-publish.sh:308-325` — The new deny arms cover reviewer *transcripts* and `claude-plan-*.prompt`, but not the Cursor/Codex plan-review *prompt files* that `dispatch-plan-review-panel.sh` writes at session root (`render-plan-cursor-${archetype}.prompt`, `render-plan-codex-${archetype}.prompt`, and `render-plan-*-dyn-${slug}.prompt`; see `skills/design/scripts/dispatch-plan-review-panel.sh:189-244`). Those files embed the same sensitive material as excluded outputs (feature description, full plan text, dynamic scout bodies via `render-plan-review-prompt.sh:132-146`), and committed design logs already flush them at top level (e.g. `larch-logs/design/*/render-plan-cursor-arch.prompt`). Excluding transcripts while leaving these prompts publishable leaves a large deny-completeness hole relative to the #3534 “findings canonical / raw plan-review excluded” goal, and the updated `SECURITY.md` / `design-log-publish.md` prose overstates coverage. **Suggested fix:** Add producer-backed deny patterns for `render-plan-cursor-*.prompt` and `render-plan-codex-*.prompt` (static + dyn) in `design_artifact_excluded()`, pin them in `scripts/test-design-log-publish.sh`, and document them beside `claude-plan-*.prompt` in `SECURITY.md` and `scripts/design-log-publish.md`.
- **Suggested revision**: Address the concern above.

### FINDING_28: **architecture** `scripts/design-log-publish.sh:308-325` — Plan-quality assessor artifacts remain top-level publishable: `claude-plan-assessor-round-<N>.txt`, `codex-plan-assessor-round-<N>.txt`, `cursor-plan-assessor-round-<N>.txt`, plus `.json` sidecars (`assess-plan-round.sh:171-179`, `dispatch-plan-assessors.sh:71-73`). They do not match `claude-plan-*-output*.txt` (plan explicitly defers them), but they are raw external/Claude transcripts comparing plan revisions with `ASSESSMENT` / `REASONING` / `QUALIFICATIONS` content—same sensitivity class as excluded plan-review outputs. After this branch tightens reviewer-transcript exclusion, assessor outputs become the obvious remaining raw-LLM leak at top level. **Suggested fix:** Either add explicit deny patterns for `*-plan-assessor-round-*.txt` and `*-plan-assessor-round-*.txt.json` (and optionally `assessor-verdict-round-*.txt*`) if policy matches round-N/findings-canonical, or document in `SECURITY.md` / `design-log-publish.md` that assessor transcripts are intentionally published and why that differs from plan-review reviewer exclusion.
- **Reviewer**: dyn-deny-completeness-output.txt
- **Concern**: - **architecture** `scripts/design-log-publish.sh:308-325` — Plan-quality assessor artifacts remain top-level publishable: `claude-plan-assessor-round-<N>.txt`, `codex-plan-assessor-round-<N>.txt`, `cursor-plan-assessor-round-<N>.txt`, plus `.json` sidecars (`assess-plan-round.sh:171-179`, `dispatch-plan-assessors.sh:71-73`). They do not match `claude-plan-*-output*.txt` (plan explicitly defers them), but they are raw external/Claude transcripts comparing plan revisions with `ASSESSMENT` / `REASONING` / `QUALIFICATIONS` content—same sensitivity class as excluded plan-review outputs. After this branch tightens reviewer-transcript exclusion, assessor outputs become the obvious remaining raw-LLM leak at top level. **Suggested fix:** Either add explicit deny patterns for `*-plan-assessor-round-*.txt` and `*-plan-assessor-round-*.txt.json` (and optionally `assessor-verdict-round-*.txt*`) if policy matches round-N/findings-canonical, or document in `SECURITY.md` / `design-log-publish.md` that assessor transcripts are intentionally published and why that differs from plan-review reviewer exclusion.
- **Suggested revision**: Address the concern above.

### FINDING_29: **architecture** `scripts/test-design-log-publish.sh:461-576` — The expanded deny-loop fixtures thoroughly cover transcript basenames, producer-backed sidecars, and collector failure logs, but omit any negative assertion for `render-plan-*.prompt` (or top-level `scout-plan-manifest.json`, which carries `prompt_body` used to build dynamic prompts). That means the harness cannot catch the largest remaining prompt-bearing gap even if deny patterns are added later. **Suggested fix:** Add excluded fixtures such as `render-plan-cursor-arch.prompt` and `render-plan-codex-dyn-foo.prompt` to the denied-basename loop (and positive control that canonical `plan-review/round-1/scout-plan-manifest.json` still publishes when placed under the allowlisted tree).
- **Reviewer**: dyn-deny-completeness-output.txt
- **Concern**: - **architecture** `scripts/test-design-log-publish.sh:461-576` — The expanded deny-loop fixtures thoroughly cover transcript basenames, producer-backed sidecars, and collector failure logs, but omit any negative assertion for `render-plan-*.prompt` (or top-level `scout-plan-manifest.json`, which carries `prompt_body` used to build dynamic prompts). That means the harness cannot catch the largest remaining prompt-bearing gap even if deny patterns are added later. **Suggested fix:** Add excluded fixtures such as `render-plan-cursor-arch.prompt` and `render-plan-codex-dyn-foo.prompt` to the denied-basename loop (and positive control that canonical `plan-review/round-1/scout-plan-manifest.json` still publishes when placed under the allowlisted tree).
- **Suggested revision**: Address the concern above.

### FINDING_30: [OUT_OF_SCOPE] **Pre-existing dead round-N pattern:** `scripts/lib-design-round-artifacts.sh:242` still lists `dyn-*-output.txt`, but real dynamic outputs are `cursor-plan-dyn-*-output.txt` and `codex-primary-plan-dyn-*-output.txt` (`dispatch-plan-review-panel.sh:234-243`). This branch only repairs the sibling dead `codex-plan-*` pattern; behavior is unchanged because the round-N catch-all still excludes real names via the `cursor-plan-*` / `codex-primary-plan-*` arms.
- **Reviewer**: dyn-deny-completeness-output.txt
- **Concern**: - **Pre-existing dead round-N pattern:** `scripts/lib-design-round-artifacts.sh:242` still lists `dyn-*-output.txt`, but real dynamic outputs are `cursor-plan-dyn-*-output.txt` and `codex-primary-plan-dyn-*-output.txt` (`dispatch-plan-review-panel.sh:234-243`). This branch only repairs the sibling dead `codex-plan-*` pattern; behavior is unchanged because the round-N catch-all still excludes real names via the `cursor-plan-*` / `codex-primary-plan-*` arms.
- **Suggested revision**: Address the concern above.

### FINDING_31: [OUT_OF_SCOPE] **Cursor/Codex `.stderr` / `.stderr-tail` omission is consistent with producers:** `launch-review.sh` routes launcher stderr to `.sidecar` / optional `--stderr-sink`, not `${OUTPUT}.stderr` / `.stderr-tail`; only `launch-claude-subprocess.sh` writes those suffixes (`scripts/launch-claude-subprocess.sh:205-231`). The branch correctly limits Claude-only `.stderr*` sidecars.
- **Reviewer**: dyn-deny-completeness-output.txt
- **Concern**: - **Cursor/Codex `.stderr` / `.stderr-tail` omission is consistent with producers:** `launch-review.sh` routes launcher stderr to `.sidecar` / optional `--stderr-sink`, not `${OUTPUT}.stderr` / `.stderr-tail`; only `launch-claude-subprocess.sh` writes those suffixes (`scripts/launch-claude-subprocess.sh:205-231`). The branch correctly limits Claude-only `.stderr*` sidecars.
- **Suggested revision**: Address the concern above.

### FINDING_32: [OUT_OF_SCOPE] **Collector failure-log slot prefixes match production:** `plan-review-loop.sh:1076-1080` derives `${slot}-collector.failure.log` from manifest slots (`cursor-plan-*`, `codex-plan-*`, `dyn-cursor-plan-*`, `dyn-codex-plan-*`, or `unknown-slot` at line 859). The deny list covers those families; a dedicated `claude-plan-*-collector.failure.log` arm is unnecessary for the plan-review panel because Claude generic failures map to `unknown-slot`.
- **Reviewer**: dyn-deny-completeness-output.txt
- **Concern**: - **Collector failure-log slot prefixes match production:** `plan-review-loop.sh:1076-1080` derives `${slot}-collector.failure.log` from manifest slots (`cursor-plan-*`, `codex-plan-*`, `dyn-cursor-plan-*`, `dyn-codex-plan-*`, or `unknown-slot` at line 859). The deny list covers those families; a dedicated `claude-plan-*-collector.failure.log` arm is unnecessary for the plan-review panel because Claude generic failures map to `unknown-slot`.
- **Suggested revision**: Address the concern above.

### FINDING_33: **architecture** `scripts/design-log-publish.md:38-41`, `scripts/design-log-publish.sh:316-317`, `SECURITY.md:49-53` — The updated docs state that codex `.json` sidecars have no producers and are intentionally omitted from `design_artifact_excluded()`, but `launch-review.sh` copies every non-empty reviewer `OUTPUT` to `${OUTPUT}.json` for both `cursor` and `codex` (`scripts/launch-review.sh:1149-1150`), including phased names such as `codex-primary-plan-arch-output-phase2.txt.json`. The code excludes only `cursor-plan-*-output*.txt.json` (`scripts/design-log-publish.sh:313`); codex-primary `.json` files are not denied, so they still pass the gate and are published via the `*-output*.json` trim branch (`scripts/design-log-publish.sh:360-364`). Committed design logs already contain many `codex-primary-plan-*-output-phase2.txt.json` artifacts under `larch-logs/design/`, so the new documentation overstates the publication boundary and leaves a real leak after transcript exclusion. **Suggested fix:** Add `codex-primary-plan-*-output*.txt.json` to the plan-review deny branch in `design_artifact_excluded()`, pin a phased fixture in `scripts/test-design-log-publish.sh`, and align `scripts/design-log-publish.md` and `SECURITY.md` to list codex `.json` among excluded producer-backed sidecars (or document an explicit, tested exception if strip-and-publish is intended).
- **Reviewer**: dyn-doc-code-parity-output.txt
- **Concern**: - **architecture** `scripts/design-log-publish.md:38-41`, `scripts/design-log-publish.sh:316-317`, `SECURITY.md:49-53` — The updated docs state that codex `.json` sidecars have no producers and are intentionally omitted from `design_artifact_excluded()`, but `launch-review.sh` copies every non-empty reviewer `OUTPUT` to `${OUTPUT}.json` for both `cursor` and `codex` (`scripts/launch-review.sh:1149-1150`), including phased names such as `codex-primary-plan-arch-output-phase2.txt.json`. The code excludes only `cursor-plan-*-output*.txt.json` (`scripts/design-log-publish.sh:313`); codex-primary `.json` files are not denied, so they still pass the gate and are published via the `*-output*.json` trim branch (`scripts/design-log-publish.sh:360-364`). Committed design logs already contain many `codex-primary-plan-*-output-phase2.txt.json` artifacts under `larch-logs/design/`, so the new documentation overstates the publication boundary and leaves a real leak after transcript exclusion. **Suggested fix:** Add `codex-primary-plan-*-output*.txt.json` to the plan-review deny branch in `design_artifact_excluded()`, pin a phased fixture in `scripts/test-design-log-publish.sh`, and align `scripts/design-log-publish.md` and `SECURITY.md` to list codex `.json` among excluded producer-backed sidecars (or document an explicit, tested exception if strip-and-publish is intended).
- **Suggested revision**: Address the concern above.

### FINDING_34: **architecture** `scripts/design-log-publish.md:37-40`, `scripts/lib-design-round-artifacts.md:27`, `scripts/lib-design-round-artifacts.sh:14` — The top-level publish contract now documents plan-review sidecars with a `*-output*.txt.<suffix>` anchor so phased names like `cursor-plan-arch-output-phase2.txt.meta` are covered, but the round-artifact contract still documents and implements only `*-output.txt.<suffix>` patterns (`*-output.txt.meta`, `*-output.txt.json`, etc.). Phased sidecar basenames therefore do not match the documented round exclude patterns; they are dropped only by the implicit `*) return 1` catch-all in `design_round_artifact_included()`. `lib-design-round-artifacts.md` matches `.sh` byte-for-byte on the changed line, but the two gates now document different suffix grammars without explaining that round-N relies on catch-all for phased artifacts. **Suggested fix:** Either widen the round exclude patterns to `*-output*.txt.<suffix>` (with tests for phased fixtures) or add an explicit note in both `.md` files that phased plan-review sidecars are excluded only via the round gate catch-all, while the top-level gate uses the broader `*-output*.txt` patterns.
- **Reviewer**: dyn-doc-code-parity-output.txt
- **Concern**: - **architecture** `scripts/design-log-publish.md:37-40`, `scripts/lib-design-round-artifacts.md:27`, `scripts/lib-design-round-artifacts.sh:14` — The top-level publish contract now documents plan-review sidecars with a `*-output*.txt.<suffix>` anchor so phased names like `cursor-plan-arch-output-phase2.txt.meta` are covered, but the round-artifact contract still documents and implements only `*-output.txt.<suffix>` patterns (`*-output.txt.meta`, `*-output.txt.json`, etc.). Phased sidecar basenames therefore do not match the documented round exclude patterns; they are dropped only by the implicit `*) return 1` catch-all in `design_round_artifact_included()`. `lib-design-round-artifacts.md` matches `.sh` byte-for-byte on the changed line, but the two gates now document different suffix grammars without explaining that round-N relies on catch-all for phased artifacts. **Suggested fix:** Either widen the round exclude patterns to `*-output*.txt.<suffix>` (with tests for phased fixtures) or add an explicit note in both `.md` files that phased plan-review sidecars are excluded only via the round gate catch-all, while the top-level gate uses the broader `*-output*.txt` patterns.
- **Suggested revision**: Address the concern above.

### FINDING_35: **architecture** `scripts/design-log-publish.md:35-36`, `scripts/lib-design-round-artifacts.md:27`, `scripts/lib-design-round-artifacts.sh:8` — The top-level deny list and `design-log-publish.md` document three transcript families including `claude-plan-*-output*.txt`, but `lib-design-round-artifacts.md` / `design_round_artifact_included()` still list only `cursor-plan-*-output.txt`, `codex-primary-plan-*-output.txt`, and `dyn-*-output.txt`. `claude-plan-generic-output.txt` is excluded at publish time by the new top-level branch (`scripts/design-log-publish.sh:310`) but has no named exclude pattern in the round allowlist docs or code (again relying on catch-all). **Suggested fix:** Add `claude-plan-*-output.txt` to the round exclude patterns in `scripts/lib-design-round-artifacts.sh`, `scripts/lib-design-round-artifacts.md`, and `scripts/test-lib-design-round-artifacts.sh` so the round contract matches the top-level transcript families already documented in `design-log-publish.md`.
- **Reviewer**: dyn-doc-code-parity-output.txt
- **Concern**: - **architecture** `scripts/design-log-publish.md:35-36`, `scripts/lib-design-round-artifacts.md:27`, `scripts/lib-design-round-artifacts.sh:8` — The top-level deny list and `design-log-publish.md` document three transcript families including `claude-plan-*-output*.txt`, but `lib-design-round-artifacts.md` / `design_round_artifact_included()` still list only `cursor-plan-*-output.txt`, `codex-primary-plan-*-output.txt`, and `dyn-*-output.txt`. `claude-plan-generic-output.txt` is excluded at publish time by the new top-level branch (`scripts/design-log-publish.sh:310`) but has no named exclude pattern in the round allowlist docs or code (again relying on catch-all). **Suggested fix:** Add `claude-plan-*-output.txt` to the round exclude patterns in `scripts/lib-design-round-artifacts.sh`, `scripts/lib-design-round-artifacts.md`, and `scripts/test-lib-design-round-artifacts.sh` so the round contract matches the top-level transcript families already documented in `design-log-publish.md`.
- **Suggested revision**: Address the concern above.

### FINDING_36: [OUT_OF_SCOPE] architecture
- **Reviewer**: dyn-doc-code-parity-output.txt
- **Concern**: - **architecture** `scripts/lib-design-round-artifacts.md:23` — The documented include basename list still omits `findings-in-scope.pre-dedup.md` and `plan-review-scope-anchor.txt`, which are included in `scripts/lib-design-round-artifacts.sh:17-23`. Pre-existing doc drift, not introduced by this branch.
- **Suggested revision**: Address the concern above.

### FINDING_37: [OUT_OF_SCOPE] architecture
- **Reviewer**: dyn-doc-code-parity-output.txt
- **Concern**: - **architecture** `scripts/lib-design-round-artifacts.md:27`, `scripts/lib-design-round-artifacts.sh:8` — The `dyn-*-output.txt` exclude pattern remains documented and coded but does not match real `/design` plan-review producers (`cursor-plan-dyn-*-output.txt`, `codex-primary-plan-dyn-*-output.txt`). The branch fixed the fictional `codex-plan-*` name but left this legacy pattern; behavior is unchanged because dynamic outputs are covered by the cursor/codex-primary patterns.
- **Suggested revision**: Address the concern above.

