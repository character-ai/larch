### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: nit
- **Focus area**: architecture
- **Location**: scripts/test-design-log-publish.md:6-10
- **Concern**: Harness sibling doc not listed in plan updates. Scenario: Coverage list stays stale after new symlink cases; script-md-siblings drift
- **Proposed resolution**: Add render-cache symlink rejection to the harness coverage bullets in the same PR

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/test-design-log-publish.sh:627+
- **Concern**: No render-cache leaf file-symlink test. Scenario: Regression in find -type l for file symlinks (vs directory symlinks) could slip through; plan-review leaf case at 561-573 is uncovered
- **Proposed resolution**: Add a render-cache test mirroring linked-plan.txt: symlink a file under render-cache and assert PUBLISH_OK=false

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: nit
- **Focus area**: architecture
- **Location**: plan.txt:151-152
- **Concern**: Case A does not exercise new tree-wide guard. Scenario: Implementer may think Case A validates the new stanza; it only re-checks the pre-existing root -L guard
- **Proposed resolution**: Document that Case A is dir-level regression; Case B/C validate the new checks

### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md:28-37
- **Concern**: Plan hardens a security-relevant artifact publication path but omits the required SECURITY.md update. Scenario: AGENTS.md requires SECURITY.md updates when security-relevant behavior changes; after this lands, SECURITY.md would still mention event-stream exclusion and breadcrumb symlink failure but not render-cache fail-closed symlink handling
- **Proposed resolution**: Add SECURITY.md to the plan and document that design render-cache publication rejects render-cache root symlinks, symlinks anywhere under the resolved render-cache root, and per-file symlink races before staging

### FINDING_5:
- **Reviewer(s)**: Codex-Arch
- **Severity**: nit
- **Focus area**: correctness
- **Location**: scripts/design-log-publish.md:23-26
- **Concern**: The proposed documentation edit says to remove the top-level symlink behavior even though that contract remains true. Scenario: Top-level DESIGN_TMPDIR symlinks are still skipped by maxdepth regular-file enumeration; replacing that clause with only render-cache subtree language makes the contract less accurate and may imply top-level symlink behavior changed
- **Proposed resolution**: Preserve the top-level artifact sentence and add render-cache as a separate clause, e.g. Top-level symlinks are skipped; plan-review/ and render-cache/ fail closed on symlinks in their guarded subtrees

### FINDING_6:
- **Reviewer(s)**: Cursor-Edge, Cursor-Edge
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md:139-139
- **Concern**: Plan omits SECURITY.md update while hardening render-cache publish. Scenario: Post-PR SECURITY.md still documents plan-review symlink fail-closed only; operators reading security policy miss that render-cache now rejects subtree symlinks
- **Proposed resolution**: Add a SECURITY.md step: extend the design-log-publish bullet to state render-cache/ uses the same tree-wide find -type l sweep and per-file -L recheck as plan-review/

### FINDING_7:
- **Reviewer(s)**: Cursor-Edge, Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-log-publish.sh:627-627
- **Concern**: Proposed harness mirrors only 3 of 5 plan-review symlink patterns; symlink-file case omitted. Scenario: plan-review exercises a leaf symlink at 569-573; render-cache relies on the new tree-wide find -type l for file symlinks (find -type f never lists them). Removing lines 305-310 analog without a file-symlink test could regress to PUBLISH_OK=true with silent omission
- **Proposed resolution**: Add a fourth case: ln -s "$TMP/design/plan.txt" "$TMP/design/render-cache/linked.txt" and assert PUBLISH_OK=false (mirror TMPPRS at 569-573)

### FINDING_8:
- **Reviewer(s)**: Cursor-Edge, Cursor-Edge
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/design-log-publish.sh:210-212
- **Concern**: Per-file -L guard does not fail closed through design_publish_stage_file. Scenario: Same-UID swap between [[ -L $f ]] and design_publish_stage_file leaves a symlink; stage_file returns 0 for -L sources so publish stays PUBLISH_OK=true with the path omitted
- **Proposed resolution**: After the -L guard call design_publish_stage_file only via a wrapper that errors on symlink, or change design_publish_stage_file to return 1 on -L for publish paths (note in plan Edge cases)

### FINDING_9:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/design-log-publish.sh:352-356
- **Concern**: Dangling render-cache root symlink still bypasses the proposed rejection. Scenario: The plan inserts the new symlink checks inside the existing [[ -e "$DESIGN_TMPDIR/render-cache" ]] block, but [[ -e ]] is false for a broken symlink, so a dangling render-cache symlink is treated as a missing optional cache and publish succeeds despite the proposed "real directory, not a symlink" contract
- **Proposed resolution**: Change the outer guard to [[ -e "$DESIGN_TMPDIR/render-cache" || -L "$DESIGN_TMPDIR/render-cache" ]] before the root -L check, and add a dangling root symlink regression case

### FINDING_10:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: security
- **Location**: AGENTS.md:17-19; SECURITY.md:139
- **Concern**: Security-relevant behavior omits SECURITY.md update. Scenario: The plan hardens committed design-log publication at a public-boundary artifact path, but the repo instructions require SECURITY.md updates for security-relevant behavior and the existing design-log paragraph only documents plan-review symlink rejection
- **Proposed resolution**: Update SECURITY.md:139 to mention render-cache root and subtree symlink fail-closed behavior alongside plan-review

### FINDING_11:
- **Reviewer(s)**: Codex-Edge
- **Severity**: latent
- **Focus area**: security
- **Location**: scripts/design-log-publish.sh:205-247; scripts/design-log-publish.sh:387-388
- **Concern**: Per-file symlink recheck does not fully close the staging race. Scenario: The proposed [[ -L "$f" ]] check catches replacement before that line, but a file can still become a symlink before design_publish_stage_file's own check and be silently skipped, or after that check and before cp where cp follows the symlink into trim/redact staging
- **Proposed resolution**: For hardened subtree calls, make design_publish_stage_file fail rather than silently skip symlink/non-regular sources and add a post-copy/source revalidation or equivalent no-follow staging path; narrow the docs if full race closure is intentionally out of scope

### FINDING_12:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md:139-139
- **Concern**: Plan updates design-log-publish.md but not SECURITY.md. Scenario: SECURITY.md still documents plan-review symlink fail-closed only; render-cache parity is a security-relevant publish-boundary change per AGENTS.md
- **Proposed resolution**: Add a sentence to the design-log publish bullet that render-cache/ uses the same tree-wide symlink reject and per-file recheck as plan-review/

### FINDING_13:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md:139
- **Concern**: FINDING 1: SECURITY.md is omitted even though this is a security-relevant publish-boundary hardening. Scenario: Repo instructions require SECURITY.md updates for security-relevant behavior changes; after the PR, auditors would still see only plan-review documented as fail-closed on subtree symlinks while render-cache has silently gained the same refusal behavior
- **Proposed resolution**: Add SECURITY.md to the plan and update the /design design-log publish paragraph to state that render-cache must be a real directory and any symlink under it fails publish before staging

### FINDING_14:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/design-log-publish.sh:379-388
- **Concern**: FINDING 2: The proposed leaf-only symlink recheck does not close parent-directory replacement races. Scenario: The plan claims the per-file [[ -L "$f" ]] closes the find-to-stage race, but an attacker can replace render-cache/nested with a symlink after enumeration; $f still has the under-root string prefix and the leaf can be a regular file through the symlinked parent, so cp/redaction can read outside the cache
- **Proposed resolution**: Add a parent-component/physical-parent validation immediately before staging and a regression test that swaps an enumerated parent directory for an external symlink; if full TOCTOU closure is out of reach in portable shell, narrow the docs to avoid claiming the race is closed

### FINDING_15:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: nit
- **Focus area**: architecture
- **Location**: scripts/design-log-publish.sh:289-396
- **Concern**: FINDING 3: The plan copies another bespoke tree-staging block instead of removing the drift source. Scenario: This issue exists because plan-review and render-cache staging evolved separately; duplicating the same symlink, prefix, enumeration, and staging logic leaves future hardening to be patched in two places again
- **Proposed resolution**: Consider extracting a small shared staging helper with parameters for subtree name, destination prefix, and optional relpath validator; keep render-cache deny-only by passing no allowlist validator while sharing the safety checks

### FINDING_16:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-log-publish.sh:627
- **Concern**: Plan adds three render-cache symlink tests but omits the in-tree file-symlink case that plan-review already covers at 561-573. Scenario: Symlink files under render-cache are not listed by find -type f; without the tree-wide find -type l guard publish can succeed while design_publish_stage_file silently skips symlinks (210-212). No harness asserts that regression
- **Proposed resolution**: Add a fourth case mirroring 561-573: ln -s a real file inside design/render-cache/ and assert PUBLISH_OK=false (exercises the new tree-wide check, not only root/intermediate/race)

### FINDING_17:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: security
- **Location**: scripts/design-log-publish.sh:377-388
- **Concern**: Render-cache race recheck only tests the final path component. Scenario: A file enumerated as render-cache/nested/c.txt can have nested replaced by a symlink before staging; [[ -L "$f" ]] stays false and cp follows the symlinked parent, staging outside content
- **Proposed resolution**: Add a pre-stage ancestor/canonical-path check for the file directory against rc_root, or walk rel directory components rejecting -L; add a render-cache parent-directory symlink race test

### FINDING_18:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-log-publish.sh:627-133
- **Concern**: Plan mirrors only three plan-review symlink cases and omits the leaf symlink-file case at scripts/test-design-log-publish.sh:561-573. Scenario: Symlink files under render-cache are not enumerated by find -type f; without a dedicated case, a broken or removed tree-wide find -type l pre-scan could regress to silent skip via design_publish_stage_file (scripts/design-log-publish.sh:210-211) while intermediate-dir and race tests still pass
- **Proposed resolution**: Add a fourth harness case after Case B mirroring plan-review: mkdir render-cache/round or nested dir, ln -s an external file into render-cache, assert PUBLISH_OK=false

### FINDING_19:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: security
- **Location**: AGENTS.md:17-19; SECURITY.md:139
- **Concern**: The plan changes security-relevant publish behavior but omits the required SECURITY.md update. Scenario: Repo instructions require SECURITY.md updates for security-relevant behavior changes, and SECURITY.md currently documents only plan-review as failing closed on subtree symlinks; after this PR, render-cache would also have that security posture but the plan leaves the security policy stale
- **Proposed resolution**: Add SECURITY.md to the plan and update the /design design-log publish paragraph to state that render-cache must be a real directory and fails publish on any symlink under its subtree, while preserving the distinction that render-cache has no filename allowlist

### FINDING_20:
- **Reviewer(s)**: Cursor-dyn-doc-sync
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/test-design-log-publish.md:6-10
- **Concern**: Plan adds three render-cache symlink harness cases but omits updating the harness coverage paragraph. Scenario: Contributors read test-design-log-publish.md and believe render-cache lacks symlink-rejection coverage while plan-review has it
- **Proposed resolution**: Extend the coverage list to mention render-cache symlink rejection (root, intermediate-directory, find→stage race) alongside the existing render-cache recursive-staging line; design-log-publish.md Tests section (102-105) can stay minimal like today

### FINDING_21:
- **Reviewer(s)**: Cursor-dyn-insertion-anchor
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/design-log-publish.sh:363-368
- **Concern**: Tree-wide symlink anchor prose cites line 367 as the rc_root assignment; line 367 is the closing brace of the || { ... } error handler (assignment starts at 363). Scenario: Implementer treats "current line 367" as the rc_root line and inserts the find -type l stanza inside the failure-only || { } block (e.g. before the closing }) so the check runs only when cd/pwd -P fails, or never on the success path
- **Proposed resolution**: Revise the plan anchor to: insert after the closing } of the render-cache canonicalization block (line 367), immediately before _rc_files=$(mktemp ...) (line 368); cite lines 363-367 for the full rc_root || { ... } block, not line 367 alone as the assignment

### FINDING_22:
- **Reviewer(s)**: Codex-dyn-insertion-anchor
- **Severity**: nit
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:11; scripts/design-log-publish.sh:363-368
- **Concern**: Tree-wide symlink insertion anchor has mismatched prose and line number: the rc_root assignment starts at scripts/design-log-publish.sh:363, while line 367 is the closing brace of the || { ... } error-handler block.. Scenario: The intended insertion between lines 367 and 368 is correct, because it lands after the full error-handler and before _rc_files mktemp allocation; however, following the prose literally as immediately after the assignment line could place the new check inside the error handler.
- **Proposed resolution**: Revise the plan text to say insert after the rc_root resolution block, specifically after the closing brace at scripts/design-log-publish.sh:367 and before _rc_files at line 368.

