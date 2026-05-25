Producing the merged structured finding list from the supplied reviewer inputs. No file edits or mutating commands were used.

### FINDING_1: Fenced collect-agent-results example conflicts with conditional path rules
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The fenced collector example always passes two paths while surrounding prose requires omitting non-external slots, forbidding zero-path calls, and matching Step 2a-style dynamic argv. An orchestrator that copies the fence can invoke the collector on paths that were never launched as externals, hit wrong or empty files, or fail to reconcile the example with Step 2a.3-style guards.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Replace static fence with one-path/two-path examples and explicit copy-paste warning tied to actual launches.

### FINDING_2: Scope vs framing output paths ambiguous under waterfall and lane swaps
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Under waterfall fallback and non-deterministic lane or tool order, slot-to-output filename mapping is unclear: operators may write synthesis inputs to the wrong deterministic path, parent writes may target the wrong canonical file, the same vendor output path may be reused twice, or framing and scope roles may be mixed in synthesis. Non-deterministic “adjust” language for output filenames exacerbates ambiguity when lanes swap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Pin canonical per-slot filenames independent of which vendor executed, or use distinct staging files per slot.

### FINDING_3: Step 1d.5 breadcrumb UX: duplicates and premature banner on skip paths
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Step 1d.5 start messaging is duplicated when both the SKILL and brainstorm.md entry guard print a start line; operators following both files literally can print the same step-start twice. Separately, the orange step banner can print before brainstorm.md decides to skip (e.g. off-path `/design --simple`), so acceptance wording that only names the skip line may not match visible logs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Gate timing/print on brainstorm_requested or reorder so skip is the only user-visible 1d.5 line when skipped.
  - From cursor-specialist-plan-fidelity-output.txt: Remove one of the duplicate Print directives (prefer deleting brainstorm.md entry-guard step 4 or not printing in SKILL before the reference runs)

### FINDING_4: Released [42.4.16] changelog understates shipped /design --brainstorm surface
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Release notes for [42.4.16] call out other changes (e.g. ship-pr key drift harness) but omit the public `--brainstorm` / `brainstorm_requested` / Step 1d.5 behavior shipped on the branch, so operators relying on the changelog may miss user-visible behavior for that version tag.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Add a concise Changed bullet for --brainstorm / Step 1d.5 aligned with the version bump.
  - From cursor-specialist-edge-cases-output.txt: Add bullet or adjust versioning per changelog policy.

### FINDING_5: [OUT_OF_SCOPE] Final summary jq uses `.classification` while run-params stores `design_classification`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Summary mode jq reads `.classification` but run-params uses `design_classification`, so classification display may always fall back to N/A; reviewers treat this as pre-existing on main, not introduced by the brainstorm work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Switch jq to .design_classification (or add a JSON alias) in a dedicated cleanup.
  - From cursor-specialist-edge-cases-output.txt: Align jq field name in a separate fix.

### FINDING_6: [OUT_OF_SCOPE] `test-implement-structure.sh` ship-pr key extraction coupled to fragile `ship-pr.sh` formatting
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The drift-guard awk range is anchored to patterns (e.g. a literal `} > "$tmp" && mv` tail inside `write_initial_state`) that can break or narrow incorrectly on non-semantic refactors or whitespace changes to `ship-pr.sh`, producing false-positive key drift or harness failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Anchor on explicit markers inside write_initial_state
  - From cursor-specialist-testing-output.txt: Anchor extraction on a dedicated comment marker inside write_initial_state instead of the redirect line
  - From cursor-specialist-edge-cases-output.txt: Anchor on stable markers or exported key-list helper

### FINDING_7: Already-planned ad-hoc Q&A with `--brainstorm` can exit before tier/run-params materialization
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: When an issue already has `larch:plan`, `/design --brainstorm` without a tier flag, and the operator chooses ad-hoc Q&A, the literal exit path can run Q&A before items that materialize tier/run-params (e.g. items 5–6). That can leave `write-run-params` inputs undefined, omit `brainstorm_requested: true` in run-params, and cause the Step 1d.5 entry guard to skip despite plan acceptance language—unless tier gate and run-params write are enforced (or a single default tier is documented and implemented) before Q&A.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Add jq -e or helper precondition before Q&A exit.

### FINDING_8: `plan-review-loop.sh` merges `brainstorm.md` into plan-review context without tests guarding the contract
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The script merges `brainstorm.md` into `plan-review-feature-context.txt` before scout/panel, but tests never create `brainstorm.md`, assert merged output, or validate `--feature-file` wiring. A refactor could drop the merge, reorder it after validation, or pass the wrong path while CI still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a stubbed tmpdir scenario with non-empty brainstorm.md plus assertions on the merged artifact and/or a dispatch stub that logs the resolved --feature-file path.

### FINDING_9: `--brainstorm` orchestration branches are prose-only with no offline harness
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Pre–Step-0, tier-gate, already-planned Q&A, and related `--brainstorm` flows rely on AskUserQuestion-style prose contracts only; accidental deletion or reordering of upgrade/cancel vs Q&A vs Step 1d.5 would not be caught by grep-based structure tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Either accept as orchestration-only risk or add minimal structure tests pinning critical literals (option labels, Step 1d.5 MANDATORY pointer before Q&A exit).

### FINDING_10: Merged brainstorm text in plan-review feature context expands prompt-injection surface for reviewers
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `brainstorm.md` (from externals plus operator-edited synthesis) is appended into the same artifact as issue context for scout/panel, so adversarial or model-injected instructions in brainstorm prose can bias or jailbreak the review panel without compromising shell scripts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Separate channels or explicit untrusted annex framing in the renderer, digest/size caps before merge, and argv-safe prompt delivery (--prompt-file) in normative launch docs

### FINDING_11: `brainstorm_requested` can diverge from argv when jq/write-run-params is degraded
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Persistence that depends on jq plus Step 1d.5 consulting only `run-params.json` can drop argv `--brainstorm` intent when `write-run-params` fails or jq is absent: warnings may print while JSON omits `brainstorm_requested: true`, so Step 1d.5 skips despite the user passing `--brainstorm`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add fail-closed recovery, argv consistency check in brainstorm entry, or mandatory operator prompt when JSON disagrees with argv.

### FINDING_12: `.brainstorm-done` short-circuit skips without the same visibility as `brainstorm_requested=false`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The sentinel-hit path can short-circuit without the visible skip breadcrumb used when brainstorm is disabled, making re-entry logs look like silent no-ops and incident triage harder.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Emit a distinct skip breadcrumb for sentinel-hit path.

### FINDING_13: Non-atomic merge write for `plan-review-feature-context.txt`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: If the merge write is not atomic, interruption mid-merge can yield truncated context fed to scout/panel without a hard failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Use temp file plus atomic mv.

### FINDING_14: [OUT_OF_SCOPE] Branch bundles brainstorm with unrelated harness, logs, and plan-surface churn
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The same change-set mixes the brainstorm feature with unrelated dedup/harness edits, high-volume log assets, and paths beyond a tight #2754 trace, increasing review noise, bisect/revert cost, and conflict risk unless the plan explicitly lists every co-delivered path or work is split.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Track as separate PR or commit for reviewers.
  - From cursor-specialist-plan-fidelity-output.txt: Split unrelated commits/PRs or update the authoritative plan to list every co-delivered path explicitly

---

There are 14 merged `### FINDING_N:` blocks, so **`LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` must not appear** anywhere in this output.
