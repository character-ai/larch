### FINDING_1: Duplicate marker when upsert delegates to tracking-issue-summary.sh
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements, Codex-Arch, Cursor-Edge, Codex-Edge, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Codex-Requirements, Cursor-dyn-doc-drift-sweep, Codex-dyn-doc-drift-sweep, Cursor-dyn-shell-contract-fit, Codex-dyn-shell-contract-fit
- **Severity**: important
- **Concern**: The planned `upsert-diagrams-comment.sh` composes a body that already starts with the `larch:diagrams` marker, then passes that file to `tracking-issue-summary.sh upsert-summary` with the same `--marker`. `upsert-summary` unconditionally prepends `MARKER` + blank line + content (see `scripts/tracking-issue-summary.sh:58-59`), producing duplicate marker lines, breaking exact first-line matching on subsequent upserts, and drifting dry-run/parser expectations from the published GitHub body.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Cursor-Innovation, Cursor-Requirements: Pass --content-file with section bodies only (no marker); reserve marker for --marker. Document in upsert-diagrams-comment.md; dry-run may print full preview including marker separately
  - From Codex-Arch: Define the helper's delegated content file as sections-only when calling tracking-issue-summary.sh, or bypass tracking-issue-summary.sh for publication; keep dry-run responsible for printing the full marker-plus-sections preview if needed.
  - From Cursor-Edge: Pass --content-file with merged sections only (no marker); let upsert-summary own the marker line, or document a new upsert mode that accepts a precomposed full body without re-prefixing
  - From Codex-Edge: Make the file passed to tracking-issue-summary.sh contain only section content, with dry-run rendering the marker separately, or add a complete-body mode that does not prepend MARKER
  - From Codex-Innovation: Make upsert-diagrams-comment.sh pass marker-free section content to tracking-issue-summary.sh, or bypass that wrapper only if the helper owns the final marker wrapping itself
  - From Cursor-Pragmatic: Pass --content-file with section bodies only (no marker line); keep full marker+sections only for --dry-run and parse input
  - From Codex-Pragmatic: Compose/pass only the section content file to tracking-issue-summary.sh, or change the plan so the helper owns the full HTTP upsert instead of using upsert-summary
  - From Codex-Requirements: Revise scripts/upsert-diagrams-comment.sh plan so the content file passed to tracking-issue-summary.sh contains only the section body; render marker plus section body only for dry-run/full-body display, or add an explicit tracking-issue-summary mode that accepts a full body without prepending
  - From Codex-dyn-doc-drift-sweep: Revise the plan so the helper keeps two payloads: a full marker-prefixed body only for parsing/dry-run display, and a markerless content file passed to tracking-issue-summary.sh upsert-summary
  - From Cursor-dyn-shell-contract-fit: Specify --content-file holds only H2 sections (no marker); keep marker solely on upsert-summary --marker
  - From Codex-dyn-shell-contract-fit: Revise the plan so upsert-diagrams-comment.sh writes only the Architecture and Code Flow sections to the --content-file passed to tracking-issue-summary.sh; keep the stable marker only in the --marker argument. If --dry-run should show the final remote body, document that it renders marker plus sections without using that same file as the upsert content.


### FINDING_2: Existing comment fetch must return full multiline bodies
- **Reviewer(s)**: Codex-Edge, Codex-Innovation
- **Severity**: important
- **Concern**: The plan reuses `tracking-issue-summary.sh`'s listing pattern (`gh api` jq returning only `id` + first line of body). That cannot preserve multiline Architecture/Code Flow sections; a later upsert may silently treat prior sections as absent and drop them, or force an untested second fetch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Specify a JSON-safe full-body fetch for the new helper, for example gh api comments --paginate --jq '.[] | {id:.id, body:(.body // "")} | tojson' parsed with jq, using the decoded first line only for marker matching; add a multiline body test with tabs and literal backslash-n text
  - From Codex-Innovation: Specify a full-body fetch contract, such as gh api comments JSONL with id and body or a second issues/comments/{id} fetch after exactly one marker match, and pin byte-preservation in the new harness


### FINDING_3: Code Flow placeholder overwrites valid section on skip/failure
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Concern**: The planned `code-flow-section.md` placeholder on generation skip/failure is non-empty, so the shared helper will replace a previously valid issue-scoped Code Flow section with "not available" during a small/non-runtime rerun or transient generator outage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Only create/pass code-flow-section.md when STATUS=ok, letting absent/empty mean preserve prior; if no prior exists, omit Code Flow rather than writing a placeholder unless an explicit replace-with-placeholder mode is requested


### FINDING_4: agent-lint.toml retains stale compose-architecture-sketch exclusions
- **Reviewer(s)**: Codex-Arch, Cursor-dyn-deletion-call-graph, Codex-dyn-deletion-call-graph
- **Severity**: important
- **Concern**: The deletion plan removes `scripts/test-compose-architecture-sketch.{sh,md}` and Makefile references but omits `agent-lint.toml` dead-script exclusions and comments (`agent-lint.toml:1436-1447` still reference the deleted harness). Post-merge config drift misleads reachability policy and may affect lint.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Remove the compose-architecture-sketch entries and related comment text from agent-lint.toml, and broaden the final grep to include agent-lint.toml or run a repo-wide grep.
  - From Cursor-dyn-deletion-call-graph: Add agent-lint.toml to Files to modify: remove scripts/test-compose-architecture-sketch.sh and .md from [lint] exclude, update the issue #2042 comment block (and fix stale test-harnesses-4 shard note to test-harnesses-20)
  - From Codex-dyn-deletion-call-graph: Update agent-lint.toml in the same change: remove the test-compose-architecture-sketch exclude entries and revise the nearby comment to cover only compose-pr-summary, then widen the final verification grep to include agent-lint.toml or repo-wide excluding larch-logs


### FINDING_5: mermaid-safe-content.md still describes larch-log diagrams batch
- **Reviewer(s)**: Codex-Arch
- **Severity**: latent
- **Concern**: The plan moves diagram ownership to an issue-scoped `larch:diagrams` helper and says diagrams are not a larch-log batch, but `skills/shared/mermaid-safe-content.md` still names a larch-log diagrams sanitizer and requires updates when publication behavior changes. Consumers may preserve outdated enforcement assumptions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Update skills/shared/mermaid-safe-content.md to describe the new issue-scoped larch:diagrams helper, the remaining PR Code Flow embed, and the absence of a diagrams larch-log batch.


### FINDING_6: Anti-halt chain and harness pins omit new Step 5c.5
- **Reviewer(s)**: Codex-Innovation, Cursor-dyn-doc-drift-sweep, Cursor-dyn-deletion-call-graph
- **Severity**: important
- **Concern**: The plan adds `/design` Step 5c.5 (diagrams upsert) but does not update `skills/design/SKILL.md:30` anti-halt transition list (`5c.1→5c.7→5c.8` skips `5c.5`) or `scripts/test-design-structure.sh:590` grep pin (`5→5a→5b→5c.1→5c.7→5c.8→6`). `make lint` / `test-design-structure` can fail after SKILL.md edit, or orchestrators may halt after the diagrams upsert breadcrumb.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add scripts/test-design-structure.sh to UPDATED and revise the pinned 5c sequence checks to include the diagrams sub-step
  - From Cursor-dyn-doc-drift-sweep: Add `scripts/test-design-structure.sh` to FILES; update `skills/design/SKILL.md:30` to `5→5a→5b→5c.1→5c.5→5c.7→5c.8→6` and adjust check (17) expected literal
  - From Cursor-dyn-deletion-call-graph: Explicitly add 5c.5 to the anti-halt continuation reminder chain and to any Step 5c prose that lists publish sub-steps


### FINDING_7: SECURITY.md not updated for new public diagram comment boundary
- **Reviewer(s)**: Codex-Innovation, Codex-Requirements
- **Severity**: important
- **Concern**: Architecture diagrams move to a `/design` GitHub comment public boundary via `scripts/upsert-diagrams-comment.sh`, but the plan omits `SECURITY.md`. Operators and reviewers retain the old trust model (slim marker summaries, implementation/PR-time Mermaid) while `/design` posts architecture content earlier; repo policy requires `SECURITY.md` updates for security-relevant behavior changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Update SECURITY.md to document scripts/upsert-diagrams-comment.sh, /design Step 5c.5, the stable issue-scoped larch:diagrams marker, and the redaction/sanitizer boundaries alongside the existing tracking-summary and Mermaid paragraphs
  - From Codex-Requirements: Add SECURITY.md to the plan, documenting the new helper, stable issue-scoped larch:diagrams marker, public Architecture/Code Flow payload behavior, redaction order/delegation to tracking-issue-summary.sh, and failure handling


### FINDING_8: Stale Architecture section when /design skips diagram generation
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: `/design` skips the helper when the new plan has no architecture diagram, so an existing Architecture section is never cleared. A rerun on the same issue after replacing an architectural plan with a non-architectural one leaves the old Architecture Diagram in the stable `larch:diagrams` comment; `/implement` then preserves that stale section while updating Code Flow.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Add an explicit clear-architecture path for /design's Step 3b skip case, or make Step 5c.5 call the helper with an owner-aware mode that removes Architecture when /design intentionally produced no diagram


### FINDING_9: Missing harness coverage that /design Step 5c.5 invokes the helper
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The testing plan does not assert that `/design` Step 5c actually invokes the new helper after `plan-block-write` when `architecture-diagram.md` exists. Helper unit tests alone can pass while `SKILL.md` never wires the design call, gates it incorrectly, or logs failures in the wrong category.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Extend scripts/test-design-structure.sh or add an equivalent design harness assertion for the Step 5c.5 helper call, architecture file existence guard, post-plan-block-write ordering, no-op skip path, and Warnings logging on UPSERT_STATUS=failed


### FINDING_10: Final orphan verification grep too narrow
- **Reviewer(s)**: Cursor-dyn-deletion-call-graph, Codex-dyn-deletion-call-graph
- **Severity**: important
- **Concern**: The plan's final `grep -rn compose-architecture-sketch scripts/ skills/ Makefile` probe is narrower than the actual reference surface. Post-merge it can return zero while `agent-lint.toml` still references the deleted script/harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-deletion-call-graph: Extend the plan's final verification to grep -rn compose-architecture-sketch . (or at minimum include agent-lint.toml) and require a clean agent-lint.toml edit in the same commit
  - From Codex-dyn-deletion-call-graph: Update agent-lint.toml in the same change: remove the test-compose-architecture-sketch exclude entries and revise the nearby comment to cover only compose-pr-summary, then widen the final verification grep to include agent-lint.toml or repo-wide excluding larch-logs

---

**Merge summary**: 26 reviewer slots → 10 distinct findings. Highest-consensus issue: duplicate marker delegation (14 reviewers). No empty merge; `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` not included.

