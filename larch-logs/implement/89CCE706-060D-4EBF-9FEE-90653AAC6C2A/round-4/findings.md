Verifying a few key code references so merged findings stay accurate.
Structured aggregator output (plain text; no empty-merge attestation).

### FINDING_1: `reviewer-testing` plan injection missing despite folded plan-fidelity
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, cursor-specialist-security-output.txt, dyn-vendor-parity-output.txt, dyn-contract-sync-output.txt, dyn-prompt-context-output.txt
- **Severity**: important
- **Concern**: `scripts/render-specialist-prompt.sh` only embeds `<implementation_plan>` / `<feature_description>` when `MODE=diff` and `DIFF_MODE=generic` (lines 298–308). There is no `reviewer-testing` basename exception. In docs-only, test-only, generated-only, and description-mode runs, `reviewer-testing` runs without plan context even though `dispatch-panel.sh` requires `--plan-file` and `agents/reviewer-testing.md` defines a plan-fidelity secondary scan. Folded plan-fidelity checks are weakened on common PR shapes; plan-only security or acceptance criteria may not reach the testing specialist.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add reviewer-testing-only emit_untrusted_file_block for PLAN_FILE across diff modes and description mode
  - From cursor-specialist-testing-output.txt: Branch on agent basename and inject redacted plan/feature for reviewer-testing across all diff modes and description mode
  - From cursor-specialist-edge-cases-output.txt: Branch on agent_base=reviewer-testing: emit redacted implementation_plan whenever PLAN_FILE is readable, all diff modes and description mode; narrow generic gate to other agents; fix tests.
  - From cursor-specialist-plan-fidelity-output.txt: Add a reviewer-testing-only branch that emits implementation_plan (and feature_description when set) for all diff modes and description mode; keep other agents on generic-only injection.
  - From cursor-specialist-security-output.txt: If plan-bound checks are still required, reintroduce `reviewer-testing`-only injection via `emit_untrusted_file_block` for all modes (with `redact-secrets.sh` + markup escaping already used in round 3), or document that plan-fidelity secondary scanning is intentionally limited to generic diffs and accept the coverage gap in acceptance criteria.
  - From dyn-vendor-parity-output.txt: After loading `agent_base` (`scripts/render-specialist-prompt.sh:197`), inject plan (and optionally feature) for `reviewer-testing` in all diff modes and in description mode; flip `scripts/test-render-specialist-prompt.sh:1538-1550` to `assert_contains` for those cases; keep `assert_not_contains` guards on non-testing agents only.
  - From dyn-contract-sync-output.txt: After the generic injection block, add a branch keyed on `agent_base=reviewer-testing` (and optionally `reviewer-testing` only for feature file) that calls `emit_untrusted_file_block` for all diff modes and for `MODE=description`, then flip `scripts/test-render-specialist-prompt.sh` to `assert_contains` for those cases and align `SECURITY.md`.
  - From dyn-prompt-context-output.txt: Either implement the documented `reviewer-testing` basename exception (inject via `emit_untrusted_file_block` for all diff modes + description, with tests flipped to `assert_contains`), or narrow all docs/agent copy/dispatch errors to match the generic-only gate and drop the false “injects folded plan-fidelity” wording.

### FINDING_2: Harness locks in absent plan injection for `reviewer-testing`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, cursor-specialist-security-output.txt, dyn-vendor-parity-output.txt, dyn-artifact-retention-output.txt, dyn-contract-sync-output.txt
- **Severity**: important
- **Concern**: `scripts/test-render-specialist-prompt.sh` (≈375–387) uses `assert_not_contains` so `reviewer-testing` must not receive plan text in docs-only, test-only, generated-only, and description modes. That matches current renderer behavior but contradicts `scripts/render-specialist-prompt.md:33`, harness contract group 13, and plan acceptance. CI stays green while cross-mode plan injection for folded plan-fidelity is untested or actively rejected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Flip to assert_contains for reviewer-testing; keep assert_not_contains for other agents
  - From cursor-specialist-testing-output.txt: Replace assert_not_contains with assert_contains for reviewer-testing; add non-testing negative matrix and generic positive case
  - From cursor-specialist-plan-fidelity-output.txt: Change assertions to assert_contains for reviewer-testing plan injection; add explicit positive cases; keep reviewer-correctness negative guards.
  - From cursor-specialist-security-output.txt: Either restore the `reviewer-testing` exception using the same `emit_untrusted_file_block` + `redact-secrets.sh` path as generic mode, or update `render-specialist-prompt.md`, `test-render-specialist-prompt.md`, and dispatch comments so they match the narrowed, generic-only injection policy.
  - From dyn-vendor-parity-output.txt: Make contract, tests, and `render-specialist-prompt.sh` agree on one rule: either implement the exception and use positive assertions, or narrow the `.md` contract if plan injection is intentionally deferred (and drop the mandatory `--plan-file` requirement for non-generic paths).
  - From dyn-contract-sync-output.txt: Either implement the `reviewer-testing` exception in `render-specialist-prompt.sh` and change the assertions to `assert_contains`, or rewrite the `.md` contract and plan acceptance to state that plan injection remains generic-only (and drop the mandatory `--plan-file` rationale tied to folded plan-fidelity outside generic diff).

### FINDING_3: Plan-injection policy drift across md, sh, SECURITY.md, agents, and tests
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-security-output.txt, dyn-prompt-context-output.txt, dyn-contract-sync-output.txt
- **Severity**: important
- **Concern**: `scripts/render-specialist-prompt.md:33` documents a `reviewer-testing` exception across all diff modes and description mode; `scripts/render-specialist-prompt.sh` implements generic-only injection; `SECURITY.md` (≈113–117) states generic-diff-only plan emission; `scripts/test-render-specialist-prompt.sh` and `scripts/test-render-specialist-prompt.md` disagree with each other and with acceptance. `agents/reviewer-testing.md` still instructs reviewers to use `<implementation_plan>` when present. Operators and security readers get conflicting trust-boundary guidance; implementers cannot land acceptance without fighting tests or docs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Implement testing exception in sh; sync md, SECURITY.md, and tests together.
  - From cursor-specialist-correctness-output.txt: Implement exception or revert doc claim
  - From cursor-specialist-testing-output.txt: Update prose to match implemented renderer rules including reviewer-testing exception
  - From cursor-specialist-edge-cases-output.txt: Update SECURITY.md to match renderer contract after fix
  - From cursor-specialist-security-output.txt: Align `render-specialist-prompt.md` with `SECURITY.md` and the implementation (pick one policy and make all three match).
  - From dyn-prompt-context-output.txt: Align `SECURITY.md` with the chosen behavior (if the exception is implemented, document it; if not, remove the exception from `render-specialist-prompt.md` and acceptance text).
  - From dyn-contract-sync-output.txt: Narrow the sentence to non-testing specialists for generic diff only, and explicitly document that `reviewer-testing` may receive redacted plan blocks in other modes when `PLAN_FILE` is set.

### FINDING_4: `larch-log.sh` excludes dynamic Codex twin artifacts contrary to acceptance
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-vendor-parity-output.txt, dyn-artifact-retention-output.txt, dyn-contract-sync-output.txt
- **Severity**: important
- **Concern**: `round_artifact_included` in `scripts/larch-log.sh` (line 77) denies `dyn-*-codex-output.txt` and sidecars while unphased `dyn-*-output.txt` (Cursor dynamic) remains allow-listed via `*-output.txt` (line 95). Committed implement run logs retain Cursor dynamic transcripts but drop Codex dynamic twins, breaking vendor-symmetric post-merge forensics and contradicting acceptance (“exclude static `codex-specialist-*` but not `dyn-*-codex` twins”).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Remove dynamic Codex twin prefixes from deny list; update larch-log.md and test-larch-log-write-round.sh.
  - From cursor-specialist-correctness-output.txt: Remove dyn codex entries from deny list; fix tests and larch-log.md
  - From cursor-specialist-testing-output.txt: Remove dynamic Codex patterns from round_artifact_included denylist and align larch-log.md plus test-larch-log-write-round.sh
  - From cursor-specialist-plan-fidelity-output.txt: Remove dyn-*-codex from deny list if acceptance stands, or update acceptance/plan to codify exclusion and drop the contradictory acceptance bullet.
  - From dyn-vendor-parity-output.txt: Remove the four `dyn-*-codex-output.*` entries from the deny arm in `round_artifact_included`, align `scripts/larch-log.md` and `scripts/test-larch-log-write-round.sh` with “static Codex excluded, dynamic Codex twins included” (assert files are copied), and keep the static `codex-specialist-*` deny precise so it does not over-match dynamics.
  - From dyn-artifact-retention-output.txt: Remove the `dyn-*-codex-output.txt` (and sidecar) tokens from the exclusion case at line 77 so dynamic Codex twins follow the same retention path as dynamic Cursor outputs; keep static `codex-specialist-*-output.txt` excluded. Update `scripts/larch-log.md:30-32` to document inclusion, not exclusion.
  - From dyn-contract-sync-output.txt: Remove `dyn-*-codex-output.txt` and its `.meta`/`.json`/`.cap-hit` patterns from the deny list in `round_artifact_included`, update `larch-log.md`, and change the harness to `assert_file` for a dynamic Codex twin fixture while keeping static `codex-specialist-*` excluded.

### FINDING_5: `test-larch-log-write-round.sh` codifies dynamic Codex exclusion
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-artifact-retention-output.txt
- **Severity**: important
- **Concern**: Regression harness (≈119–121) uses `assert_not_file` for `dyn-api-contract-codex-output.txt` and sidecars, opposite of plan acceptance. CI locks in forensics loss; there is no paired positive control that a sibling Cursor dynamic output is still included, so vendor asymmetry is not guarded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-artifact-retention-output.txt: Flip the dynamic Codex assertions to `assert_file` (with redaction/`CMD_JSON` checks mirroring other included sidecars), add a Cursor-dynamic fixture with `assert_file`, and align `scripts/test-larch-log-write-round.md:11-12` with the intended contract.

### FINDING_6: Per-archetype coverage gate ignores `cap_hit` successes
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `static_archetype_coverage_ok` in `skills/review/scripts/review-core.sh` (≈447–448) credits only `STATUS=OK`. The aggregate failure threshold treats `cap_hit` as success via `status_is_success`, so a both-vendor panel can pass the >50% gate then fail coverage when peers return `cap_hit` with partial output, failing the round as `panel-failed`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Unify cap_hit semantics across threshold and coverage or document intentional strictness.
  - From cursor-specialist-correctness-output.txt: Align coverage with threshold or document stricter policy
  - From cursor-specialist-edge-cases-output.txt: Treat cap_hit as coverage success (aligned with threshold) or require substantive output file; add regression harness.

### FINDING_7: Scout fields embedded without redaction/escaping in dynamic prompts
- **Reviewer(s)**: dyn-prompt-context-output.txt
- **Severity**: important
- **Concern**: In `skills/review/scripts/dispatch-panel.sh` (≈168–173), scout `rationale` and `prompt_body` are written into `<scout_notes>` without `redact-secrets.sh` or angle-bracket escaping, while plan/feature blocks use `emit_untrusted_file_block`. Validation blocks closing scout/reviewer tags but not delimiter-shaped strings such as `<implementation_plan encoding="literal-redacted">` inside `prompt_body`. A malicious or jailbroken scout could plant markup after a legitimately escaped plan block; Codex dynamic twins reuse the same pre-rendered prompt.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-context-output.txt: Pipe scout fields through the same `redact_untrusted_stream` helper (or `escape_prompt_data`) before embedding in `synthesize_dynamic_slots`, extend `scout_manifest_is_valid` to reject plan/feature delimiter patterns, and add a harness with a malicious `prompt_body` proving escaped output.

### FINDING_8: `count_static_status_once` never downgrades false-positive successes
- **Reviewer(s)**: dyn-waterfall-accounting-output.txt
- **Severity**: important
- **Concern**: In `skills/review/scripts/check-reviewer-failure-threshold.sh` (≈138–158), `count_static_status_once` only upgrades failure→success. When collector results say `OK`/`cap_hit` but `--reviewer-output-files` is empty or non-substantive (`output_file_is_success` → `ERROR`), the slot can remain in `SUCCEEDED_SLOTS`, weakening the >50% gate and diverging from coverage (which only credits `STATUS=OK`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-waterfall-accounting-output.txt: Extend `count_static_status_once` with a symmetric downgrade path (e.g. when `status_is_success(old)` and the new status is `ERROR`/`NOT_SUBSTANTIVE`, decrement `SUCCEEDED_SLOTS` and increment `FAILED_SLOTS`), or treat a failed `output_file_is_success` check as authoritative over collector `OK` for the same normalized base.

### FINDING_9: Dropped-static accounting with empty `dropped_base` inflates failures
- **Reviewer(s)**: dyn-waterfall-accounting-output.txt
- **Severity**: important
- **Concern**: In `check-reviewer-failure-threshold.sh` (≈208–227), dropped-static handling increments `FAILED_SLOTS`/`DROPPED_STATIC_SLOTS` even when `dropped_base` is empty (unrecognized `_dropped_tool`), adding failure without a normalized base in `COUNTED_BASES_FILE` and inflating `FAILED_SLOTS` vs the 8-slot denominator.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-waterfall-accounting-output.txt: `continue` before incrementing when `dropped_base` is empty after the `codex|cursor` case, or increment only when a normalized base was newly recorded.

### FINDING_10: Duplicate static slot IDs across Cursor and Codex
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `skills/review/scripts/dispatch-panel.sh` (≈97) reuses the same manifest `slot` slug for Cursor and Codex static peers (`security`, etc.), unlike design review’s vendor-prefixed slots. Drop accounting still disambiguates via `tool`, but slot-keyed diagnostics and cross-skill manifest comparison are ambiguous.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Mirror design-style distinct slot names if safe for tally

### FINDING_11: Duplicated `normalize_reviewer_output_base` risks threshold/coverage desync
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `normalize_reviewer_output_base` is duplicated in `review-core.sh` and `check-reviewer-failure-threshold.sh` (≈594–610). Suffix-handling changes can desync threshold math from the coverage gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract shared lib and source both scripts from it.

### FINDING_12: Dead structure/plan-fidelity mappings in vote tally
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `skills/review/scripts/tally-code-votes.sh` (≈288–293) retains dead structure and plan-fidelity focus mappings after archetype collapse, adding confusing maintenance surface before conditional spawning work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Remove dead case arms or document legacy-only attribution.

---

### FINDING_13: [OUT_OF_SCOPE] Description-mode preamble embeds raw `DESCRIPTION_TEXT`
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-prompt-context-output.txt
- **Severity**: latent
- **Concern**: `scripts/render-specialist-prompt.sh` (≈289–295) interpolates `'${DESCRIPTION_TEXT}'` in trusted prose without `redact-secrets.sh` or markup escaping. Pre-existing prompt-injection surface; not introduced by this branch (`scout-dynamic-archetypes.sh` already uses `escape_prompt_data` for similar data).
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_14: [OUT_OF_SCOPE] Standalone `security` archetype preserved in static panel
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Positive: standalone `security` remains in `static_specialists`; structure/plan-fidelity folded into other lenses without removing the dedicated security slot — aligns with the issue’s “security must stay standalone” decision.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_15: [OUT_OF_SCOPE] Generic-diff plan injection hardening (round 3)
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-prompt-context-output.txt
- **Severity**: nit
- **Concern**: Positive: generic-mode plan/feature embedding uses `redact-secrets.sh` plus `encoding="literal-redacted"` wrappers (`emit_untrusted_file_block`); regression coverage for tag escaping and token redaction exists in `scripts/test-render-specialist-prompt.sh`.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_16: [OUT_OF_SCOPE] Codex phase-1 re-enable within documented read-only posture
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Positive: `codex_present_for_waterfall="$CODEX_AVAILABLE"` stays within existing read-only Codex/Cursor review posture in `SECURITY.md`; conditional `--no-fallback` when both vendors are up avoids duplicate Codex fallback runs.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_17: [OUT_OF_SCOPE] `static_archetype_coverage_ok` limits silent lens loss
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Positive: per-archetype coverage fails the round if `security`, `correctness`, `edge-cases`, or `testing` has zero successful static peers, so a lone dropped Cursor peer cannot silently eliminate the security lens when Codex also failed.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_18: [OUT_OF_SCOPE] Dropped-slot logging uses redaction
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Positive: dropped-slot logging uses `append-tool-failure.sh` with `--redact`; dynamic scout still treats `prompt_body` as untrusted inside `<scout_notes>`.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_19: [OUT_OF_SCOPE] Reviewer view: intentional raw Codex transcript reduction in run logs
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Some reviewers treat exclusion of static `codex-specialist-*` and `dyn-*-codex-output.txt` as documented intentional reduction (aggregate artifacts canonical). In-scope findings above treat dynamic Codex twin exclusion as contradicting stated acceptance — disposition is a product/acceptance choice, not a classic vulnerability.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_20: [OUT_OF_SCOPE] `--launched-slots` equals `--intended-slots` on production path
- **Reviewer(s)**: dyn-waterfall-accounting-output.txt
- **Severity**: latent
- **Concern**: `review-core.sh` (≈611–616) sets `--launched-slots` to the same value as `--intended-slots`, so `NEVER_LAUNCHED` / `UNACCOUNTED_NEVER_LAUNCHED` in `check-reviewer-failure-threshold.sh` is unused; partial no-output accounting relies on `DROPPED_SLOTS_FILE`. Matches both-vendor behavior; differs from plan “launched vs intended” wording — document, not a functional bug given drop sidecars.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_21: [OUT_OF_SCOPE] Cross-layer both-vendor contracts largely align
- **Reviewer(s)**: dyn-waterfall-accounting-output.txt, dyn-vendor-parity-output.txt
- **Severity**: nit
- **Concern**: Positive: `STATIC_SLOT_COUNT`, `DROPPED_SLOTS_FILE`, `--no-fallback`, deduped `count_static_status_once`, no short-circuit on `STATIC_DISPATCH_OK`, dynamic basename exclusion from static denominator, and harnesses for 1-of-8 pass, 5-of-8 fail, dropped-wire, and coverage-on-drops align with stated both-vendor design.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_22: [OUT_OF_SCOPE] Code review vs plan-review slot naming divergence
- **Reviewer(s)**: dyn-vendor-parity-output.txt
- **Severity**: latent
- **Concern**: Code review reuses manifest `slot` slugs across vendors; plan review uses vendor-prefixed slots. Drop accounting disambiguates via `tool`; operators comparing manifests across skills should expect different naming.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_23: [OUT_OF_SCOPE] Threshold counts finals, not all phase2 paths
- **Reviewer(s)**: dyn-vendor-parity-output.txt
- **Severity**: latent
- **Concern**: Threshold `--reviewer-output-files` uses dispatch final outputs only; differs from plan “count all phase2/phase3 static failures” wording. Failed finals plus `DROPPED_SLOTS_FILE` cover both-vendor `--no-fallback` paths in practice.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_24: [OUT_OF_SCOPE] `--competition-notice-file` still unredacted
- **Reviewer(s)**: dyn-prompt-context-output.txt
- **Severity**: latent
- **Concern**: `scripts/render-specialist-prompt.sh` (≈354–357) still `cat`s competition notice without redaction/escaping; pre-existing, unchanged by plan/feature hardening.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_25: [OUT_OF_SCOPE] `test-larch-log.sh` lacks static Codex deny assertion
- **Reviewer(s)**: dyn-artifact-retention-output.txt
- **Severity**: latent
- **Concern**: Broader `test-larch-log.sh` write-round section still only asserts denial for `cursor-specialist-*-output.txt`, not static `codex-specialist-*-output.txt`. Predates branch; more material now that Codex static specialists are re-enabled.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_26: [OUT_OF_SCOPE] Stale timing kinds in `lib-timing-kinds.sh`
- **Reviewer(s)**: dyn-contract-sync-output.txt
- **Severity**: latent
- **Concern**: Allowlist still includes `cursor-specialist-structure`, `cursor-specialist-plan-fidelity`, and matching `codex-specialist-*` kinds though the panel no longer dispatches those slugs. Mostly dead configuration.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_27: [OUT_OF_SCOPE] Weakened `test-quick-mode-docs-sync.sh` markers
- **Reviewer(s)**: dyn-contract-sync-output.txt
- **Severity**: latent
- **Concern**: `POS_MARKERS` no longer pins `5 rounds` or `--panel hard`, so public docs can drift on round-cap and panel argv without failing the harness (appears intentional per updated sibling `.md`).
- **Suggested revisions (informational for voters; coder decides)**:

---

**Summary:** Twelve in-scope merged findings (two **important** clusters dominate: missing `reviewer-testing` plan injection plus doc/test/SECURITY drift, and `larch-log` denying `dyn-*-codex-output` with matching harness inversion). Four additional in-scope items cover coverage/`cap_hit`, scout escaping, threshold accounting, and two nits. Fifteen `[OUT_OF_SCOPE]` items capture pre-existing surfaces, positive notes, and operator-policy disagreements on log retention.
