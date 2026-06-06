### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: code-quality: scripts/lib-design-round-artifacts.sh:8
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] PR fixes dead codex-plan-*-output.txt exclude arm but leaves dyn-*-output.txt in the same case; no producer emits output basenames starting with dyn-. Real dynamic outputs are cursor-plan-dyn-*-output.txt and codex-primary-plan-dyn-*-output.txt. Maintainers may believe dyn-*-output.txt excludes dynamic reviewer transcripts; it matches zero production basenames (same bug class as the removed codex-plan-* pattern). Harm is low because cursor-plan-* and codex-primary-plan-* patterns cover real files. Remove dyn-*-output.txt from design_round_artifact_included and lib-design-round-artifacts.md, or replace with real producer prefixes and a comment citing dispatch-plan-review-panel.sh.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_14: `eb4ed1782` — Exclude raw plan-review outputs from design-log publish (#3534)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `eb4ed1782` — Exclude raw plan-review outputs from design-log publish (#3534)
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_15: `ce56735fa` — chore(larch-logs): flush implement run (out of review scope per policy)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `ce56735fa` — chore(larch-logs): flush implement run (out of review scope per policy)
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_19: security: SECURITY.md:26-34
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] SECURITY.md documents plan-review exclusions as comprehensive but omits that render-plan-*.prompt files still publish. After merge, operators trust SECURITY.md and believe plan-review prompts are gated; render-plan-cursor/codex prompts with plan and feature text still land in larch-logs/design/<run-id>/ top level. Add explicit carve-out or extend design_artifact_excluded to deny render-plan-*.prompt; document whichever policy is chosen in design-log-publish.md.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: code-quality: scripts/design-log-publish.sh:308-325
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Plan-review exclusions are a large inline case block in design_artifact_excluded while design_round_artifact_included encodes overlapping rules with different glob strictness; edit-in-sync rule does not cover test-design-log-publish.sh for top-level deny changes. Future producer rename (e.g. new phased suffix) may update one gate or test surface and miss others, reintroducing committed raw transcripts. Extract shared basename patterns to lib-design-round-artifacts.sh or extend edit-in-sync rule to require test-design-log-publish.sh on top-level deny changes.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_20: correctness: scripts/design-log-publish.sh:322
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Collector failure denylist covers unknown-slot-collector.failure.log but not slot-collector.failure.log from empty-slug fallback. plan-review-loop.sh sanitization fallback writes slot-collector.failure.log for empty slot names; file can flush with compose-collector-failure/append-tool-failure content. Deny slot-collector.failure.log or use sole-producer *-collector.failure.log pattern with plan-review-loop.sh comment.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: code-quality: scripts/test-lib-design-round-artifacts.sh:53-56
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Round-N helper excludes phased plan-review transcripts only via default *) arm; no phased fixtures. Future allowlist edit could accidentally include phased raw transcripts while top-level gate and tests stay correct. Add assert_excluded for *-output-phase2.txt basenames; consider *-output*.txt exclude suffix in lib-design-round-artifacts.sh.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_25

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_25: `eb4ed1782` — Exclude raw plan-review outputs from design-log publish (#3534)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `eb4ed1782` — Exclude raw plan-review outputs from design-log publish (#3534)
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_26

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_26: `ce56735fa` — chore(larch-logs): flush implement run (out of scope per review rules)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `ce56735fa` — chore(larch-logs): flush implement run (out of scope per review rules) Walked the implementation plan requirement-by-requirement against commit `eb4ed1782`. The diff touches all seven planned files and matches the stated intent.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_27

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_27: **architecture** `scripts/design-log-publish.sh:308-325` — The new deny arms cover reviewer *transcripts* and `claude-plan-*.prompt`, but not the Cursor/Codex plan-review *prompt files* that `dispatch-plan-review-panel.sh` writes at session root (`render-plan-cursor-${archetype}.prompt`, `render-plan-codex-${archetype}.prompt`, and `render-plan-*-dyn-${slug}.prompt`; see `skills/design/scripts/dispatch-plan-review-panel.sh:189-244`). Those files embed the same sensitive material as excluded outputs (feature description, full plan text, dynamic scout bodies via `render-plan-review-prompt.sh:132-146`), and committed design logs already flush them at top level (e.g. `larch-logs/design/*/render-plan-cursor-arch.prompt`). Excluding transcripts while leaving these prompts publishable leaves a large deny-completeness hole relative to the #3534 “findings canonical / raw plan-review excluded” goal, and the updated `SECURITY.md` / `design-log-publish.md` prose overstates coverage. **Suggested fix:** Add producer-backed deny patterns for `render-plan-cursor-*.prompt` and `render-plan-codex-*.prompt` (static + dyn) in `design_artifact_excluded()`, pin them in `scripts/test-design-log-publish.sh`, and document them beside `claude-plan-*.prompt` in `SECURITY.md` and `scripts/design-log-publish.md`.
- **Reviewer**: dyn-deny-completeness-output.txt
- **Concern**: - **architecture** `scripts/design-log-publish.sh:308-325` — The new deny arms cover reviewer *transcripts* and `claude-plan-*.prompt`, but not the Cursor/Codex plan-review *prompt files* that `dispatch-plan-review-panel.sh` writes at session root (`render-plan-cursor-${archetype}.prompt`, `render-plan-codex-${archetype}.prompt`, and `render-plan-*-dyn-${slug}.prompt`; see `skills/design/scripts/dispatch-plan-review-panel.sh:189-244`). Those files embed the same sensitive material as excluded outputs (feature description, full plan text, dynamic scout bodies via `render-plan-review-prompt.sh:132-146`), and committed design logs already flush them at top level (e.g. `larch-logs/design/*/render-plan-cursor-arch.prompt`). Excluding transcripts while leaving these prompts publishable leaves a large deny-completeness hole relative to the #3534 “findings canonical / raw plan-review excluded” goal, and the updated `SECURITY.md` / `design-log-publish.md` prose overstates coverage. **Suggested fix:** Add producer-backed deny patterns for `render-plan-cursor-*.prompt` and `render-plan-codex-*.prompt` (static + dyn) in `design_artifact_excluded()`, pin them in `scripts/test-design-log-publish.sh`, and document them beside `claude-plan-*.prompt` in `SECURITY.md` and `scripts/design-log-publish.md`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_28

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_28: **architecture** `scripts/design-log-publish.sh:308-325` — Plan-quality assessor artifacts remain top-level publishable: `claude-plan-assessor-round-<N>.txt`, `codex-plan-assessor-round-<N>.txt`, `cursor-plan-assessor-round-<N>.txt`, plus `.json` sidecars (`assess-plan-round.sh:171-179`, `dispatch-plan-assessors.sh:71-73`). They do not match `claude-plan-*-output*.txt` (plan explicitly defers them), but they are raw external/Claude transcripts comparing plan revisions with `ASSESSMENT` / `REASONING` / `QUALIFICATIONS` content—same sensitivity class as excluded plan-review outputs. After this branch tightens reviewer-transcript exclusion, assessor outputs become the obvious remaining raw-LLM leak at top level. **Suggested fix:** Either add explicit deny patterns for `*-plan-assessor-round-*.txt` and `*-plan-assessor-round-*.txt.json` (and optionally `assessor-verdict-round-*.txt*`) if policy matches round-N/findings-canonical, or document in `SECURITY.md` / `design-log-publish.md` that assessor transcripts are intentionally published and why that differs from plan-review reviewer exclusion.
- **Reviewer**: dyn-deny-completeness-output.txt
- **Concern**: - **architecture** `scripts/design-log-publish.sh:308-325` — Plan-quality assessor artifacts remain top-level publishable: `claude-plan-assessor-round-<N>.txt`, `codex-plan-assessor-round-<N>.txt`, `cursor-plan-assessor-round-<N>.txt`, plus `.json` sidecars (`assess-plan-round.sh:171-179`, `dispatch-plan-assessors.sh:71-73`). They do not match `claude-plan-*-output*.txt` (plan explicitly defers them), but they are raw external/Claude transcripts comparing plan revisions with `ASSESSMENT` / `REASONING` / `QUALIFICATIONS` content—same sensitivity class as excluded plan-review outputs. After this branch tightens reviewer-transcript exclusion, assessor outputs become the obvious remaining raw-LLM leak at top level. **Suggested fix:** Either add explicit deny patterns for `*-plan-assessor-round-*.txt` and `*-plan-assessor-round-*.txt.json` (and optionally `assessor-verdict-round-*.txt*`) if policy matches round-N/findings-canonical, or document in `SECURITY.md` / `design-log-publish.md` that assessor transcripts are intentionally published and why that differs from plan-review reviewer exclusion.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_29

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_29: **architecture** `scripts/test-design-log-publish.sh:461-576` — The expanded deny-loop fixtures thoroughly cover transcript basenames, producer-backed sidecars, and collector failure logs, but omit any negative assertion for `render-plan-*.prompt` (or top-level `scout-plan-manifest.json`, which carries `prompt_body` used to build dynamic prompts). That means the harness cannot catch the largest remaining prompt-bearing gap even if deny patterns are added later. **Suggested fix:** Add excluded fixtures such as `render-plan-cursor-arch.prompt` and `render-plan-codex-dyn-foo.prompt` to the denied-basename loop (and positive control that canonical `plan-review/round-1/scout-plan-manifest.json` still publishes when placed under the allowlisted tree).
- **Reviewer**: dyn-deny-completeness-output.txt
- **Concern**: - **architecture** `scripts/test-design-log-publish.sh:461-576` — The expanded deny-loop fixtures thoroughly cover transcript basenames, producer-backed sidecars, and collector failure logs, but omit any negative assertion for `render-plan-*.prompt` (or top-level `scout-plan-manifest.json`, which carries `prompt_body` used to build dynamic prompts). That means the harness cannot catch the largest remaining prompt-bearing gap even if deny patterns are added later. **Suggested fix:** Add excluded fixtures such as `render-plan-cursor-arch.prompt` and `render-plan-codex-dyn-foo.prompt` to the denied-basename loop (and positive control that canonical `plan-review/round-1/scout-plan-manifest.json` still publishes when placed under the allowlisted tree).
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: code-quality: scripts/test-design-log-publish.sh:538-577
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] ~35 denied basenames are hardcoded in a for-loop parallel to design_artifact_excluded case arms with no mechanical linkage. Drift between function globs and test fixture list can pass CI while missing a newly added transcript family (prior codex-plan-* fictional fixtures demonstrated this class). Add table-driven unit assertions that call design_artifact_excluded directly; keep one integration publish smoke test.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_34

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_34: **architecture** `scripts/design-log-publish.md:37-40`, `scripts/lib-design-round-artifacts.md:27`, `scripts/lib-design-round-artifacts.sh:14` — The top-level publish contract now documents plan-review sidecars with a `*-output*.txt.<suffix>` anchor so phased names like `cursor-plan-arch-output-phase2.txt.meta` are covered, but the round-artifact contract still documents and implements only `*-output.txt.<suffix>` patterns (`*-output.txt.meta`, `*-output.txt.json`, etc.). Phased sidecar basenames therefore do not match the documented round exclude patterns; they are dropped only by the implicit `*) return 1` catch-all in `design_round_artifact_included()`. `lib-design-round-artifacts.md` matches `.sh` byte-for-byte on the changed line, but the two gates now document different suffix grammars without explaining that round-N relies on catch-all for phased artifacts. **Suggested fix:** Either widen the round exclude patterns to `*-output*.txt.<suffix>` (with tests for phased fixtures) or add an explicit note in both `.md` files that phased plan-review sidecars are excluded only via the round gate catch-all, while the top-level gate uses the broader `*-output*.txt` patterns.
- **Reviewer**: dyn-doc-code-parity-output.txt
- **Concern**: - **architecture** `scripts/design-log-publish.md:37-40`, `scripts/lib-design-round-artifacts.md:27`, `scripts/lib-design-round-artifacts.sh:14` — The top-level publish contract now documents plan-review sidecars with a `*-output*.txt.<suffix>` anchor so phased names like `cursor-plan-arch-output-phase2.txt.meta` are covered, but the round-artifact contract still documents and implements only `*-output.txt.<suffix>` patterns (`*-output.txt.meta`, `*-output.txt.json`, etc.). Phased sidecar basenames therefore do not match the documented round exclude patterns; they are dropped only by the implicit `*) return 1` catch-all in `design_round_artifact_included()`. `lib-design-round-artifacts.md` matches `.sh` byte-for-byte on the changed line, but the two gates now document different suffix grammars without explaining that round-N relies on catch-all for phased artifacts. **Suggested fix:** Either widen the round exclude patterns to `*-output*.txt.<suffix>` (with tests for phased fixtures) or add an explicit note in both `.md` files that phased plan-review sidecars are excluded only via the round gate catch-all, while the top-level gate uses the broader `*-output*.txt` patterns.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_35

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_35: **architecture** `scripts/design-log-publish.md:35-36`, `scripts/lib-design-round-artifacts.md:27`, `scripts/lib-design-round-artifacts.sh:8` — The top-level deny list and `design-log-publish.md` document three transcript families including `claude-plan-*-output*.txt`, but `lib-design-round-artifacts.md` / `design_round_artifact_included()` still list only `cursor-plan-*-output.txt`, `codex-primary-plan-*-output.txt`, and `dyn-*-output.txt`. `claude-plan-generic-output.txt` is excluded at publish time by the new top-level branch (`scripts/design-log-publish.sh:310`) but has no named exclude pattern in the round allowlist docs or code (again relying on catch-all). **Suggested fix:** Add `claude-plan-*-output.txt` to the round exclude patterns in `scripts/lib-design-round-artifacts.sh`, `scripts/lib-design-round-artifacts.md`, and `scripts/test-lib-design-round-artifacts.sh` so the round contract matches the top-level transcript families already documented in `design-log-publish.md`.
- **Reviewer**: dyn-doc-code-parity-output.txt
- **Concern**: - **architecture** `scripts/design-log-publish.md:35-36`, `scripts/lib-design-round-artifacts.md:27`, `scripts/lib-design-round-artifacts.sh:8` — The top-level deny list and `design-log-publish.md` document three transcript families including `claude-plan-*-output*.txt`, but `lib-design-round-artifacts.md` / `design_round_artifact_included()` still list only `cursor-plan-*-output.txt`, `codex-primary-plan-*-output.txt`, and `dyn-*-output.txt`. `claude-plan-generic-output.txt` is excluded at publish time by the new top-level branch (`scripts/design-log-publish.sh:310`) but has no named exclude pattern in the round allowlist docs or code (again relying on catch-all). **Suggested fix:** Add `claude-plan-*-output.txt` to the round exclude patterns in `scripts/lib-design-round-artifacts.sh`, `scripts/lib-design-round-artifacts.md`, and `scripts/test-lib-design-round-artifacts.sh` so the round contract matches the top-level transcript families already documented in `design-log-publish.md`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: risk-integration: scripts/test-design-log-publish.sh:431-580
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Happy-path publish harness asserts denied basenames but never pins a near-miss publishable basename the plan calls out of scope. A future broadening of claude-plan transcript globs (e.g. claude-plan-*.txt) could exclude claude-plan-assessor-round-N.txt while all current deny-loop assertions still pass. Add claude-plan-assessor-round-1.txt to the fixture tree and assert it is present in the published larch-logs/design/RUNPUB1/ tree after publish.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

