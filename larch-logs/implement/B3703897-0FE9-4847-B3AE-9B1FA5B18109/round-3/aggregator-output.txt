Here is the normalized aggregator output. No file or shell mutations were performed.

---

### FINDING_1: Incomplete or misleading `[PLANNED]` managed-lifecycle documentation across fix-issue surfaces
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-prefix-state-machine-output.txt
- **Concern**: Human-facing contract and comments do not consistently describe `[PLANNED]` as a machine-managed lifecycle prefix alongside `/design` and `/implement` writers: shell comments omit the design writer; `find-lock-issue.md` Verify text and examples omit `[PLANNED]` while `find-lock-issue.sh` rejects those titles; `skills/fix-issue/SKILL.md` still lists only `[IN PROGRESS]` / `[DONE]` / `[STALLED]` for eligibility, diverging from `has_managed_prefix` and runtime error strings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From dyn-prefix-state-machine-output.txt: The **Verify** step still describes managed lifecycle prefixes as only `[IN PROGRESS]` / `[DONE]` / `[STALLED]`, and the `[ROUND-TRIP]` example line omits `[PLANNED] [ROUND-TRIP] Foo`, while `skills/fix-issue/scripts/find-lock-issue.sh:144-151` treats `[PLANNED] ` as a managed prefix and rejects those issues. That makes the shipped contract doc diverge from runtime behavior for the same feature family as the new prefix. **Suggested fix:** Extend the managed-prefix enumeration and the illustrative rejected-title examples so they explicitly include `[PLANNED]` in the same form as the shell `case` arms (literal `[PLANNED] ` with the trailing space).
  - From dyn-prefix-state-machine-output.txt: The title-prefix interaction bullet still claims the eligibility filter rejects titles with only `[IN PROGRESS]` / `[DONE]` / `[STALLED]`, which is incomplete now that `[PLANNED]` is machine-managed in `find-lock-issue.sh`. **Suggested fix:** Update that sentence (and any nearby prefix lists) to add `[PLANNED]` so SKILL-level guidance matches `has_managed_prefix` and the error string at `skills/fix-issue/scripts/find-lock-issue.sh:864`.

### FINDING_2: Clarify-loop Step 3 prose should match numbered sub-step structure of Step 5b
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Step 3 packs repo resolution, publish, failure logging, conditional rename, and clarify follow-ups into one line, making ordering and guard edits error-prone compared to the numbered Step 5b block.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: Transient `gh pr create` failure when a matching PR already exists but `pr list` is momentarily empty
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Concern**: Rare race can set `PUBLISH_OK=false` and strand operators despite a valid PR; the test harness does not cover the plan-required path where create fails while list/view recovery still yields success.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Missing harness for gh pr create failure with pr list recovery Plan-required path when a PR already exists for the log branch can break without CI failing; stub always succeeds create except NO_URL case. Extend gh stub so pr create can exit non-zero while pr list/view still return 101; assert PUBLISH_OK true and merge still invoked.

### FINDING_4: [OUT_OF_SCOPE] Duplicate `has_managed_prefix` helpers evolved in parallel
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Optional consolidation / same pattern extended in parallel across `find-lock-issue.sh` and `umbrella-handler.sh`; not required for this feature.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: Missing harness for malformed `*.meta` (meta sidecar trim failure)
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Malformed `*.meta` could fail closed in production but behavior is untested relative to output JSON; no assertion that `PUBLISH_OK` is false and merge is not invoked.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_6: `insert_signal_marker` for `[PLANNED]` lacks focused regression coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Behavior change in a sourced library has no minimal assertion on `insert_signal_marker` output for `[PLANNED]` titles.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add minimal sourced harness asserting insert_signal_marker output for [PLANNED] titles.

### FINDING_7: `scripts/lib-title-markers.md` stub omits `[PLANNED]` in prefix enumeration
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-prefix-state-machine-output.txt
- **Concern**: Stub/documentation does not enumerate `[PLANNED]`; future contributors may miss syncing the stub when grammar changes (dyn-prefix reviewer frames this as markdown drift in the same class as other doc gaps, not a shell correctness bug).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add explicit prefix list line including [PLANNED].
  - From dyn-prefix-state-machine-output.txt: `scripts/lib-title-markers.md` remains a stub that does not mention `[PLANNED]` (noted in prior review chatter); same class as the markdown drift above, not a shell correctness bug.

### FINDING_8: [OUT_OF_SCOPE] Empty diff artifact and `HEAD`/`main` identity blocked diff-accurate review
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-prefix-state-machine-output.txt
- **Concern**: Precomputed diff is empty, `HEAD` and `main` resolve to the same commit, so `git diff main...HEAD` and `git log $(git merge-base HEAD main)..HEAD` are empty; reviewers cannot verify hunks, commit list, or plan item-by-plan-item fidelity against implementation intent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Point the launcher at the branch that actually contains the feature (or regenerate `round-3/diff.txt` from `git diff main...HEAD` / `git diff $(git merge-base HEAD main)...HEAD` on that branch), then rerun this reviewer with a non-empty diff so each plan bullet can be traced to hunks and commits.

### FINDING_9: `--repo` passed to `gh` without strict format or ownership validation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: A mistyped or manipulated `--repo` can route push, PR creation, and admin-merge to the wrong repository under the same credential, publishing design artifacts to the wrong default branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_10: Automated `gh pr merge --admin` after scripted push expands token-compromise blast radius
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Any actor or automation with a token that can admin-merge can land log commits on the default branch without reviews or CI, beyond ad-hoc human merges.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] Large aggregator/orchestrator edits bundled with design-log feature work
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Increases audit surface for a security-only pass on design publish without changing reviewed empty-merge attestation enforcement in `aggregate-validate.py` main(); treat as separate functional review and keep feature branches scoped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_12: `[PLANNED]` rename semantics vs clarify completion and empty `SESSION_ID` desynchronize title, labels, and log readiness
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: On the clarify path, success can `rename --state planned` before clarify comment/label steps when `SESSION_ID` is empty with no publish, so the title becomes `[PLANNED]` while `needs-design-clarification` may still be present—consumers treating `[PLANNED]` as terminal plan+log readiness can act too early. Separately, terminal Step 5b can still rename to `[PLANNED]` when `SESSION_ID` is empty, implying flushed logs without `larch-logs/design/<RUN_ID>/` on `main`, desyncing automation that pairs title to log path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Restrict planned rename on the clarify path to terminal design completion, or reorder so title only changes after clarify response + label removal and optional publish success; align booleans with product meaning of `[PLANNED]`.
  - From cursor-specialist-edge-cases-output.txt: Tie rename to successful publish when logs are required, or use a separate prefix/state for “plan only” vs “plan + logs,” and document for consumers.

### FINDING_13: `find -type f` under `render-cache/` drops symlinked files without surfacing failure
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Symlinked cache entries are omitted from published logs while publish succeeds, yielding quietly incomplete archives.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Fail closed on unexpected symlinks or log explicit skips with nonzero policy when any skip occurs.

### FINDING_14: Nested “print `printf …`” wording in `skills/design/SKILL.md` is ambiguous for orchestrators
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Orchestrators may print the word `printf` instead of emitting the warning string.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Reword as a direct instruction to emit the warning via `printf` (no nested `print` + code-span pattern).

### FINDING_15: [OUT_OF_SCOPE] `gh pr list` stub output does not mirror production JSON contract
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Harness could pass even if integration with real `gh` list parsing regressed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Optionally tighten stub to emit the same shape as production `gh pr list` for the exercised flags.

---

**Subsumed (no separate `### FINDING_N`):** Positive attestations from dyn-prefix-state-machine-output.txt that the prefix-state-machine Bash sites are internally consistent (`FINDING_23`) and that `umbrella-handler.sh` mirrors the fourth prefix (`FINDING_24`) describe absence of defect rather than a distinct fix path; they are not listed as separate findings above.

`LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` is **not** included because one or more `### FINDING_N:` blocks are present.
