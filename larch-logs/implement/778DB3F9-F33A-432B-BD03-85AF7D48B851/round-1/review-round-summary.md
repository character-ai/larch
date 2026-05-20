# Review Round 1

- Mode: `diff`
- Accepted findings: 26
- Rejected findings: 5
- Exonerated findings: 0
- Neutral findings: 1

## Accepted Findings

### FINDING_1: **architecture** `docs/review-agents.md:100` — The “Claude fallback for externals” bullet still claims that in `/review`, **“Codex down → skip all 6 Codex specialist slots”**, which matched the old HARD panel but is **false after** `dispatch-panel.sh` reduces Codex to a **single union slot** on round 1 (and none on later rounds). Downstream readers get the wrong mental model for skip behavior and voting/threshold interactions. **Suggested fix:** Rewrite that clause to describe the **one union slot** (and round gating), or point to `skills/review/scripts/dispatch-panel.md` as the authority instead of hard-coded “6 Codex specialist” language.
- **Reviewer**: dyn-panel-unification-semantics-output.txt
- **Concern**: - **architecture** `docs/review-agents.md:100` — The “Claude fallback for externals” bullet still claims that in `/review`, **“Codex down → skip all 6 Codex specialist slots”**, which matched the old HARD panel but is **false after** `dispatch-panel.sh` reduces Codex to a **single union slot** on round 1 (and none on later rounds). Downstream readers get the wrong mental model for skip behavior and voting/threshold interactions. **Suggested fix:** Rewrite that clause to describe the **one union slot** (and round gating), or point to `skills/review/scripts/dispatch-panel.md` as the authority instead of hard-coded “6 Codex specialist” language.
- **Suggested revision**: Address the concern above.


### FINDING_10: **correctness** `skills/review/scripts/dispatch-panel.sh:412-430` — Round 1 still queues a Codex-primary `codex-union` reviewer and counts/breadcrumbs it as part of the panel, so both `--panel simple` and `--panel hard` still run Codex when `CODEX_AVAILABLE=true`. A round-1 dispatch with `--dynamic-archetypes 0` now produces 7 static slots including `codex-union-output.txt`, but the requested active panel is Cursor static archetypes plus Cursor dynamic archetypes only. **Suggested fix:** Remove `queue_codex_union_slot` from the round-1 panel path, keep `static_codex=0`, update breadcrumbs/counts to only report Cursor static plus dynamic slots, and adjust the docs/tests currently asserting “Codex union” to the Cursor-only panel shape.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: - **correctness** `skills/review/scripts/dispatch-panel.sh:412-430` — Round 1 still queues a Codex-primary `codex-union` reviewer and counts/breadcrumbs it as part of the panel, so both `--panel simple` and `--panel hard` still run Codex when `CODEX_AVAILABLE=true`. A round-1 dispatch with `--dynamic-archetypes 0` now produces 7 static slots including `codex-union-output.txt`, but the requested active panel is Cursor static archetypes plus Cursor dynamic archetypes only. **Suggested fix:** Remove `queue_codex_union_slot` from the round-1 panel path, keep `static_codex=0`, update breadcrumbs/counts to only report Cursor static plus dynamic slots, and adjust the docs/tests currently asserting “Codex union” to the Cursor-only panel shape.
- **Suggested revision**: Address the concern above.


### FINDING_11: **correctness** `skills/review/scripts/dispatch-panel.sh:99-117`, `412-415` — Relative to the provided feature text (“only Cursor remains” on the active panel: static archetypes + dynamic archetypes), the dispatcher still adds a round-1 external slot with `tool":"codex"` via `queue_codex_union_slot`, so Codex remains on the active panel (as a union reviewer), not only Cursor plus dynamics. **Suggested fix:** If the ticket is authoritative, remove Codex rows from the panel manifest for these flows while keeping Codex tooling elsewhere; if the union slot is the intended design, update the feature spec and all user-facing panel descriptions so they no longer claim a Cursor-only external panel.
- **Reviewer**: dyn-cap-bounds-sweep-output.txt
- **Concern**: - **correctness** `skills/review/scripts/dispatch-panel.sh:99-117`, `412-415` — Relative to the provided feature text (“only Cursor remains” on the active panel: static archetypes + dynamic archetypes), the dispatcher still adds a round-1 external slot with `tool":"codex"` via `queue_codex_union_slot`, so Codex remains on the active panel (as a union reviewer), not only Cursor plus dynamics. **Suggested fix:** If the ticket is authoritative, remove Codex rows from the panel manifest for these flows while keeping Codex tooling elsewhere; if the union slot is the intended design, update the feature spec and all user-facing panel descriptions so they no longer claim a Cursor-only external panel.
- **Suggested revision**: Address the concern above.


### FINDING_13: **correctness** `skills/review/scripts/review-core.md:19`, `scripts/scout-dynamic-archetypes.md:7`, `scripts/write-session-env.md:35`, `scripts/test-session-env-roundtrip.md:23` — Companion documentation still states `0..4` / “0 to 4” for `--dynamic-archetypes` / `--max-archetypes` while `skills/review/scripts/dispatch-panel.sh:77-79`, `scripts/write-session-env.sh:122-125`, `scripts/scout-dynamic-archetypes.sh:168-170`, and `scripts/session-setup.sh:420-423` enforce `0..8`, so operators and doc-driven workflows see an incorrect contract. **Suggested fix:** Edit those `.md` files (and any other remaining `0..4` skill/doc references outside generated topology) so bounds, error strings, and examples match the shipped validation.
- **Reviewer**: dyn-cap-bounds-sweep-output.txt
- **Concern**: - **correctness** `skills/review/scripts/review-core.md:19`, `scripts/scout-dynamic-archetypes.md:7`, `scripts/write-session-env.md:35`, `scripts/test-session-env-roundtrip.md:23` — Companion documentation still states `0..4` / “0 to 4” for `--dynamic-archetypes` / `--max-archetypes` while `skills/review/scripts/dispatch-panel.sh:77-79`, `scripts/write-session-env.sh:122-125`, `scripts/scout-dynamic-archetypes.sh:168-170`, and `scripts/session-setup.sh:420-423` enforce `0..8`, so operators and doc-driven workflows see an incorrect contract. **Suggested fix:** Edit those `.md` files (and any other remaining `0..4` skill/doc references outside generated topology) so bounds, error strings, and examples match the shipped validation.
- **Suggested revision**: Address the concern above.


### FINDING_2: **architecture** `scripts/generate-topology-docs.sh:195` and `docs/topology.md:7` — The topology doc generator still embeds the sentence that quick-mode phrases include **`Codex generalist`**, but the branch changes `scripts/test-quick-mode-docs-sync.sh` to pin **`Codex union`** instead. Regenerating topology (`bash scripts/generate-topology-docs.sh`) will keep re-emitting the **stale pin list** and breaks the documented contract between the generator, `docs/topology.md`, and the quick-mode sync harness. **Suggested fix:** Change the generator’s prose to name **`Codex union`** (and regenerate `docs/topology.md`) so the topology projection header matches `POS_MARKERS` in `scripts/test-quick-mode-docs-sync.sh`.
- **Reviewer**: dyn-panel-unification-semantics-output.txt
- **Concern**: - **architecture** `scripts/generate-topology-docs.sh:195` and `docs/topology.md:7` — The topology doc generator still embeds the sentence that quick-mode phrases include **`Codex generalist`**, but the branch changes `scripts/test-quick-mode-docs-sync.sh` to pin **`Codex union`** instead. Regenerating topology (`bash scripts/generate-topology-docs.sh`) will keep re-emitting the **stale pin list** and breaks the documented contract between the generator, `docs/topology.md`, and the quick-mode sync harness. **Suggested fix:** Change the generator’s prose to name **`Codex union`** (and regenerate `docs/topology.md`) so the topology projection header matches `POS_MARKERS` in `scripts/test-quick-mode-docs-sync.sh`.
- **Suggested revision**: Address the concern above.


### FINDING_28: code-quality: skills/review/scripts/test-dispatch-panel.sh:1493-1510
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Tests cover invalid `9` but not a passing `--dynamic-archetypes 8` with eight archetypes. A regression that only breaks the maximum dynamic slot count might not be caught because fixtures stop at four. Add one eight-archetype fixture asserting manifest length and `DYNAMIC_SLOTS=8`.
- **Suggested revision**: Address the concern above.


### FINDING_29: correctness: docs/review-agents.md:100
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Stale text still references six Codex specialist slots for /review Readers mis-model Codex-down behavior and panel size Update fallback paragraph to union/single-slot layout
- **Suggested revision**: Address the concern above.


### FINDING_30: correctness: docs/review-agents.md:100
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Fallback prose still references six Codex specialist slots. Readers get contradictory guidance next to the updated quick-mode note about a Codex union. Rewrite the `/review` fallback bullets to match the new static layout.
- **Suggested revision**: Address the concern above.


### FINDING_31: correctness: docs/topology.md:135 vs scripts/test-quick-mode-docs-sync.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Topology intro still names `Codex generalist` in the byte-pinned phrase list while the sync harness now keys on `Codex union`. Docs-sync CI may fail or the public topology doc may advertise the wrong anchor phrase relative to the harness contract. Update generator input / regenerated `docs/topology.md` so the listed phrase matches `POS_MARKERS` and consumer expectations.
- **Suggested revision**: Address the concern above.


### FINDING_32: correctness: feature_description vs branch (dispatch-panel.sh; codex_present_for_waterfall)
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Tagged spec says Cursor-only review panel (no Codex); branch still launches a Codex union slot on round 1. Operators and CI consumers following the feature tag expect zero Codex reviewer processes in the panel; runtime still schedules Codex on round 1, so acceptance criteria for the tagged feature are not met as written. Align implementation with spec (remove union slot) or update authoritative spec and all panel docs to describe the Codex union reviewer explicitly.
- **Suggested revision**: Address the concern above.


### FINDING_34: correctness: skills/implement/SKILL.md:1332
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] HTML comment claims default dynamic cap 8 while review-and-fix defaults to 4 Orchestrators trusting SKILL anchor misconfigure scout budget vs runtime Revert comment to cap=4 or raise default to 8 consistently in scripts/tests
- **Suggested revision**: Address the concern above.


### FINDING_35: correctness: skills/implement/SKILL.md:1332
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] HTML comment claims cap=8 “by default” for implement tmpdir mode. Orchestrators may believe the runtime default is 8 while `review-and-fix.sh` still defaults to 4. Fix the comment to separate max (0–8) from implement default (4) or change the default if 8 is truly intended.
- **Suggested revision**: Address the concern above.


### FINDING_36: correctness: skills/implement/SKILL.md:1332
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Step 5 HTML comment claims dynamic-archetypes cap=8 by default in implement tmpdir mode while flag text still says default 4 and max 0-8. Orchestrator or operator may assume default 8 and mis-align Step 5 gating or session-env expectations with review-and-fix.sh (default 4). Reword comment to state default 4 in implement tmpdir and maximum allowed 8 for explicit flags or env.
- **Suggested revision**: Address the concern above.


### FINDING_37: correctness: skills/review/scripts/dispatch-panel.sh:99-117
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Still queues a Codex tool reviewer on round 1 via queue_codex_union_slot Contradicts feature brief only Cursor on panel and plan to remove Codex slots; Codex still launches when available Remove Codex manifest rows if requirement is final or revise requirements if union is intentional
- **Suggested revision**: Address the concern above.


### FINDING_38: correctness: skills/review/scripts/dispatch-panel.sh:99-119,413-430
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Round 1 still dispatches a Codex tool slot (codex-union) for both simple and hard panels. Operators expecting zero Codex reviewers on the review panel per the feature description still pay Codex cost, tokens, and dirty-tree risk on every round-1 review. Remove the union slot and Codex waterfall enablement if Cursor-only is required; otherwise revise the feature spec and plan before shipping.
- **Suggested revision**: Address the concern above.


### FINDING_39: correctness: skills/shared/topology.tsv:13
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Topology row documents a Codex union slot instead of the planned Cursor-only hard panel summary. Downstream docs and topology anchors contradict the stated “only Cursor remains” contract. Update the TSV (and regenerated topology docs) to match the agreed panel shape.
- **Suggested revision**: Address the concern above.


### FINDING_40: risk-integration: docs/review-agents.md:100
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Fallback prose still refers to skipping six Codex specialist slots under /review. Readers mis-estimate Codex outage impact and panel shape for trust-boundary planning. Update to one Codex union slot on round 1 consistent with dispatch-panel contract.
- **Suggested revision**: Address the concern above.


### FINDING_41: risk-integration: docs/review-agents.md:100
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] /review Codex fallback docs still describe skipping six Codex specialist slots. Operators may mis-diagnose Codex outages against a panel that now has one Codex union slot on round 1. Rewrite the fallback sentence for the union-based static layout.
- **Suggested revision**: Address the concern above.


### FINDING_42: risk-integration: docs/review-agents.md:100
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Stale /review Codex fallback text still references six Codex specialist slots. Operators debugging Codex outages may assume six skipped Codex slots and misread partial panel failure vs old behavior. Rewrite the /review fallback bullet to describe the single Codex union (round 1) and dynamic Cursor slots.
- **Suggested revision**: Address the concern above.


### FINDING_44: risk-integration: docs/topology.md:7
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Topology meta-line still names Codex generalist as quick-mode excluded phrase while docs sync harness pins Codex union. Conflicting documentation about which phrase is canonical for the quick-mode contract. Update the topology header sentence to Codex union (or match whatever the sync script owns).
- **Suggested revision**: Address the concern above.


### FINDING_45: risk-integration: docs/topology.md:7
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Topology preamble still names Codex generalist as the quick-mode excluded phrase while docs sync pins Codex union. Two modified artifacts disagree on the canonical quick-mode marker phrase. Update the preamble to Codex union or regenerate from an updated TSV/rule.
- **Suggested revision**: Address the concern above.


### FINDING_47: risk-integration: skills/review/scripts/dispatch-panel.sh (vs feature_description)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Ticket requires Cursor-only review panel; branch still dispatches a Codex union slot on round 1. Stakeholders expecting zero Codex reviewer invocations may be surprised by continued Codex usage on round 1. Align spec and code (remove Codex slot or re-scope the requirement to union-only).
- **Suggested revision**: Address the concern above.


### FINDING_5: **correctness** `scripts/scout-dynamic-archetypes.md:7-11` — The contract still requires `--max-archetypes 0..4` and states “capped at 4”, but `scripts/scout-dynamic-archetypes.sh` on the branch validates `--max-archetypes` up through 8 (`scripts/scout-dynamic-archetypes.sh:169-170` in the working tree). **Suggested fix:** Raise the documented range and invariant text to `0..8` / “capped at 8” so `scout-dynamic-archetypes.md` matches the executable contract.
- **Reviewer**: dyn-codex-union-slot-integrity-output.txt
- **Concern**: - **correctness** `scripts/scout-dynamic-archetypes.md:7-11` — The contract still requires `--max-archetypes 0..4` and states “capped at 4”, but `scripts/scout-dynamic-archetypes.sh` on the branch validates `--max-archetypes` up through 8 (`scripts/scout-dynamic-archetypes.sh:169-170` in the working tree). **Suggested fix:** Raise the documented range and invariant text to `0..8` / “capped at 8” so `scout-dynamic-archetypes.md` matches the executable contract.
- **Suggested revision**: Address the concern above.


### FINDING_6: **correctness** `scripts/test-session-setup-presence-defaults.sh:123-124` — After `scripts/session-setup.sh:420-423` changes the invalid-caller warning to `(must be 0..8)`, this harness still `grep -Fq`s the old `(must be 0..4)` text, so the test fails while the runtime behavior (warn and omit `LARCH_DYNAMIC_ARCHETYPES_MAX=9`) is otherwise correct. **Suggested fix:** Update the expected substring to `(must be 0..8)` and refresh `scripts/test-session-setup-presence-defaults.md:3` so the documented expectation matches the new message.
- **Reviewer**: dyn-cap-bounds-sweep-output.txt
- **Concern**: - **correctness** `scripts/test-session-setup-presence-defaults.sh:123-124` — After `scripts/session-setup.sh:420-423` changes the invalid-caller warning to `(must be 0..8)`, this harness still `grep -Fq`s the old `(must be 0..4)` text, so the test fails while the runtime behavior (warn and omit `LARCH_DYNAMIC_ARCHETYPES_MAX=9`) is otherwise correct. **Suggested fix:** Update the expected substring to `(must be 0..8)` and refresh `scripts/test-session-setup-presence-defaults.md:3` so the documented expectation matches the new message.
- **Suggested revision**: Address the concern above.


### FINDING_7: **correctness** `scripts/test-session-setup-presence-defaults.sh:123-124` — The harness still requires stderr to contain `session-setup.sh: warning: ignoring invalid LARCH_DYNAMIC_ARCHETYPES_MAX from caller-env (must be 0..4)`, but `scripts/session-setup.sh:421-423` now validates `LARCH_DYNAMIC_ARCHETYPES_MAX` with `[0-8]` and emits `(must be 0..8)`, so this assertion will not match and the test fails on the branch. **Suggested fix:** Update the `grep -Fq` expected substring to `(must be 0..8)` (and adjust any paired `.md` contract text in `scripts/test-session-setup-presence-defaults.md` if it still says `0..4`).
- **Reviewer**: dyn-codex-union-slot-integrity-output.txt
- **Concern**: - **correctness** `scripts/test-session-setup-presence-defaults.sh:123-124` — The harness still requires stderr to contain `session-setup.sh: warning: ignoring invalid LARCH_DYNAMIC_ARCHETYPES_MAX from caller-env (must be 0..4)`, but `scripts/session-setup.sh:421-423` now validates `LARCH_DYNAMIC_ARCHETYPES_MAX` with `[0-8]` and emits `(must be 0..8)`, so this assertion will not match and the test fails on the branch. **Suggested fix:** Update the `grep -Fq` expected substring to `(must be 0..8)` (and adjust any paired `.md` contract text in `scripts/test-session-setup-presence-defaults.md` if it still says `0..4`).
- **Suggested revision**: Address the concern above.


### FINDING_9: **correctness** `skills/implement/SKILL.md:1332` — The Step 5 HTML comment was changed to say `dynamic-archetypes cap=8 by default in implement tmpdir mode`, which contradicts the same skill’s own Step 5 prose at `skills/implement/SKILL.md:1360` (`otherwise 4 (implement mode default, valid up to 8)`): the numeric default when unset remains 4, while 8 is the new maximum allowed cap, not the default. **Suggested fix:** Reword the comment to distinguish default (4) from maximum (8), e.g. align it with line 1360 instead of implying 8 is the default.
- **Reviewer**: dyn-codex-union-slot-integrity-output.txt
- **Concern**: - **correctness** `skills/implement/SKILL.md:1332` — The Step 5 HTML comment was changed to say `dynamic-archetypes cap=8 by default in implement tmpdir mode`, which contradicts the same skill’s own Step 5 prose at `skills/implement/SKILL.md:1360` (`otherwise 4 (implement mode default, valid up to 8)`): the numeric default when unset remains 4, while 8 is the new maximum allowed cap, not the default. **Suggested fix:** Reword the comment to distinguish default (4) from maximum (8), e.g. align it with line 1360 instead of implying 8 is the default.
- **Suggested revision**: Address the concern above.


