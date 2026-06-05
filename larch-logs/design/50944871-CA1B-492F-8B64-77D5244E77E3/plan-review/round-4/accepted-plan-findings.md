### FINDING_1: Claude plan-review `.meta` sidecars remain publishable
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Codex-Requirements, Codex-Pragmatic, Codex-dyn-artifact-taxonomy, Codex-dyn-fixture-realism
- **Severity**: important
- **Concern**: The proposed plan-review transcript/sidecar denylist omits Claude generic `.meta` sidecars. In the both-external-reviewers-unavailable path, `claude-plan-generic-output.txt` is excluded, but `launch-claude-subprocess.sh` also writes `claude-plan-generic-output.txt.meta`, which remains default-allowed and can still be published as producer metadata.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add claude-plan-*-output*.txt.meta to the new exclusion branch, add a claude-plan-generic-output.txt.meta fixture/assertion in scripts/test-design-log-publish.sh, and include the suffix in the SECURITY.md and scripts/design-log-publish.md publication-boundary text
  - From Codex-Edge, Codex-Requirements: Add claude-plan-*-output*.txt.meta to the new exclusion branch and include a matching fixture/assertion plus doc and SECURITY.md wording.
  - From Codex-Pragmatic: Add claude-plan-*-output*.txt.meta to the new exclusion branch and include matching test/doc/security coverage alongside the other claude-plan-* sidecars.
  - From Codex-dyn-artifact-taxonomy: Add claude-plan-*-output*.txt.meta to the proposed deny branch and add the matching publish-test fixture/docs entry
  - From Codex-dyn-fixture-realism: Add claude-plan-*-output*.txt.meta to the new deny branch and add a claude-plan-generic-output.txt.meta fixture/assertion in scripts/test-design-log-publish.sh


### FINDING_4: Plan-review collector failure logs remain publishable
- **Reviewer(s)**: Codex-dyn-publication-boundary
- **Severity**: important
- **Concern**: Plan-review collector failure logs such as `<slot>-collector.failure.log` are not included in the proposed publication denylist. These files can include full reviewer output plus diagnostic, stderr-tail, and launch-stderr sections, so raw transcript bundles may still be committed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-publication-boundary: Add explicit top-level exclusions for plan-review collector failure logs in scripts/design-log-publish.sh, including static, dynamic, and generic/unknown slot names, and add fixtures/assertions in scripts/test-design-log-publish.sh


### FINDING_5: Dropped-slot diagnostics remain publishable
- **Reviewer(s)**: Codex-dyn-publication-boundary
- **Severity**: important
- **Concern**: `plan-review-slots.ndjson.output-files.dropped-slots` remains publishable even though it can contain raw reviewer output or launch-stderr snippets in slot/tool/reason/snippet rows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-publication-boundary: Add a narrow exclusion for the plan-review dropped-slots sidecar, for example plan-review-slots.ndjson.output-files.dropped-slots, and cover it in scripts/test-design-log-publish.sh


### FINDING_7: Generic Claude prompt sidecar remains publishable
- **Reviewer(s)**: Codex-dyn-fixture-realism
- **Severity**: important
- **Concern**: The plan treats `.prompt` sidecars as already excluded, but the real both-externals-down prompt file is `claude-plan-generic.prompt`, which is not matched by existing `*-output.txt.prompt` or `*-output-*.txt.prompt` deny patterns.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-fixture-realism: Add a narrow deny for claude-plan-generic.prompt or claude-plan-*.prompt and cover it with a real-name absent assertion in scripts/test-design-log-publish.sh

