### FINDING_1: Incomplete or misleading `[PLANNED]` managed-lifecycle documentation across fix-issue surfaces
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-prefix-state-machine-output.txt
- **Concern**: Human-facing contract and comments do not consistently describe `[PLANNED]` as a machine-managed lifecycle prefix alongside `/design` and `/implement` writers: shell comments omit the design writer; `find-lock-issue.md` Verify text and examples omit `[PLANNED]` while `find-lock-issue.sh` rejects those titles; `skills/fix-issue/SKILL.md` still lists only `[IN PROGRESS]` / `[DONE]` / `[STALLED]` for eligibility, diverging from `has_managed_prefix` and runtime error strings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From dyn-prefix-state-machine-output.txt: The **Verify** step still describes managed lifecycle prefixes as only `[IN PROGRESS]` / `[DONE]` / `[STALLED]`, and the `[ROUND-TRIP]` example line omits `[PLANNED] [ROUND-TRIP] Foo`, while `skills/fix-issue/scripts/find-lock-issue.sh:144-151` treats `[PLANNED] ` as a managed prefix and rejects those issues. That makes the shipped contract doc diverge from runtime behavior for the same feature family as the new prefix. **Suggested fix:** Extend the managed-prefix enumeration and the illustrative rejected-title examples so they explicitly include `[PLANNED]` in the same form as the shell `case` arms (literal `[PLANNED] ` with the trailing space).
  - From dyn-prefix-state-machine-output.txt: The title-prefix interaction bullet still claims the eligibility filter rejects titles with only `[IN PROGRESS]` / `[DONE]` / `[STALLED]`, which is incomplete now that `[PLANNED]` is machine-managed in `find-lock-issue.sh`. **Suggested fix:** Update that sentence (and any nearby prefix lists) to add `[PLANNED]` so SKILL-level guidance matches `has_managed_prefix` and the error string at `skills/fix-issue/scripts/find-lock-issue.sh:864`.


### FINDING_12: `[PLANNED]` rename semantics vs clarify completion and empty `SESSION_ID` desynchronize title, labels, and log readiness
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: On the clarify path, success can `rename --state planned` before clarify comment/label steps when `SESSION_ID` is empty with no publish, so the title becomes `[PLANNED]` while `needs-design-clarification` may still be present—consumers treating `[PLANNED]` as terminal plan+log readiness can act too early. Separately, terminal Step 5b can still rename to `[PLANNED]` when `SESSION_ID` is empty, implying flushed logs without `larch-logs/design/<RUN_ID>/` on `main`, desyncing automation that pairs title to log path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Restrict planned rename on the clarify path to terminal design completion, or reorder so title only changes after clarify response + label removal and optional publish success; align booleans with product meaning of `[PLANNED]`.
  - From cursor-specialist-edge-cases-output.txt: Tie rename to successful publish when logs are required, or use a separate prefix/state for “plan only” vs “plan + logs,” and document for consumers.


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


