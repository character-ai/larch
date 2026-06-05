# Review Round 4

- Mode: `diff`
- 9 accepted, 3 rejected (3 exonerated)

## Accepted Findings

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


