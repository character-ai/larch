### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:17
- **Concern**: Planned sub-bullet 4 omits session-tmpdir containment as a fail-closed trigger. Scenario: Readers infer only the listed symlink/hardlink/basename/redactor checks apply; code also rejects sources outside IMPLEMENT/DESIGN/REVIEW/RESEARCH tmpdirs (scripts/lib-larch-log.sh:376-402)
- **Proposed resolution**: Add explicit bullets: breadcrumbs source directory and each staged file must resolve under an active session tmpdir via larch_log_breadcrumbs_under_session_tmp; any violation aborts the whole publish

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lib-larch-log.sh:391-417
- **Concern**: Planned fail-closed text overstates leading-dot handling. Scenario: The helper iterates "$source_dir"/*, so dotfile sidecars are not visited and do not trigger the "leading dot rejects the whole directory" behavior the new SECURITY.md and docs/run-logs.md prose would promise
- **Proposed resolution**: Revise the proposed docs to describe the actual order: non-dot regular entries are inspected, symlinks and hardlinks fail closed, non-*.ndjson regular files are skipped after those checks, and leading-dot sidecars are ignored by the glob and remain session-local

### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: docs/run-logs.md:13-67
- **Concern**: The plan keeps the directory tree unchanged even though the new subsection documents design breadcrumb publication. Scenario: scripts/design-log-publish.sh publishes $DESIGN_TMPDIR/breadcrumbs into larch-logs/design/<RUN_ID>/breadcrumbs, but the visual contract still shows breadcrumbs only under implement, making the new generic breadcrumbs/ subsection look implement-only
- **Proposed resolution**: Update the ASCII tree to show breadcrumbs/ under design as well, or explicitly label the tree as abbreviated and state that the breadcrumbs/ subsection applies to any skill/run publisher that invokes larch_log_publish_breadcrumbs_shared

### FINDING_4:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:17-18
- **Concern**: Proposed sub-bullet 5 omits operational CI/warn breadcrumb warning from SECURITY.md:154-156. Scenario: The relocated paragraph explicitly warns that wait-ci/warn categories can commit CI failure strings and check names after secrets-family redaction; the plan’s sub-bullet 5 list stops at pattern/PII risk and does not require carrying that sentence forward
- **Proposed resolution**: Extend sub-bullet 5 (or add a sixth bullet) with the existing wait-ci/warn / public-boundary CI diagnostics sentence verbatim from SECURITY.md:154-156

### FINDING_5:
- **Reviewer(s)**: Codex-Edge
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: docs/run-logs.md:13-67 and planned ### breadcrumbs/ subsection; scripts/design-log-publish.sh:398
- **Concern**: Plan keeps the directory tree unchanged even while adding design breadcrumb publication semantics. Scenario: The post-change Directory structure tree still shows breadcrumbs only under implement, while the new subsection names design-log-publish.sh and $DESIGN_TMPDIR breadcrumbs; readers scanning the tree can miss that design logs may also contain larch-logs/design/<RUN_ID>/breadcrumbs
- **Proposed resolution**: Extend the ASCII tree to include design/<RUN_ID>/breadcrumbs/*.ndjson or add an explicit sentence under the subsection that design publication uses the same breadcrumbs/ directory artifact

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/larch-log.md:96-113
- **Concern**: Plan adds a second normative breadcrumb spec in SECURITY.md and docs/run-logs.md but leaves scripts/larch-log.md unchanged with every regular non-symlink file / every file redacts language while larch_log_publish_breadcrumbs_shared silently continues only *.ndjson. Scenario: Operators and /design validators treat larch-log.md as the commit verb contract and believe sidecars could be staged; SECURITY/run-logs corrections diverge from the script doc they grep first
- **Proposed resolution**: Extend the plan to either update the Breadcrumb commit artifact block in scripts/larch-log.md to match *.ndjson-only + shared helper semantics or replace that block with a single See scripts/lib-larch-log.sh larch_log_publish_breadcrumbs_shared plus bidirectional links from both new sections

### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: security
- **Location**: plan.txt:17-18
- **Concern**: Proposed residual-risk sub-bullet drops wait-ci/warn CI diagnostic guidance. Scenario: Operators may commit CI failure strings without treating them as public-boundary content
- **Proposed resolution**: Restore SECURITY.md:154-156 wait-ci/warn sentence in the new section (sub-bullet 5 or additional bullet)

### FINDING_8:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md:143-156
- **Concern**: Proposed monitor-side bullet overstates what streaming redaction guarantees. Scenario: The current streaming redactor only replaces recognized full-line regex families and PEM markers; incomplete token fragments or partial PEM markers can still pass with exit 0, so documenting that partial PEM blocks or partial token shapes never appear creates a false operator-safety guarantee
- **Proposed resolution**: Limit the bullet to recognized PEM blocks and covered token patterns, and move incomplete or non-pattern fragments into the residual sensitive-content risk bullet

### FINDING_9:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/lib-larch-log.sh:391-416
- **Concern**: Proposed fail-closed wording overstates hidden leading-dot entry handling. Scenario: The helper iterates "$source_dir"/*, so hidden entries such as .secret.ndjson or a hidden symlink are not visited and therefore do not trigger the documented leading-dot or symlink rejection, though they are also not published
- **Proposed resolution**: Revise the docs-only plan to say non-hidden enumerated entries are validated and hidden entries are ignored/not published, or explicitly expand the implementation and tests to enumerate and reject dotfiles

### FINDING_10:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md:154-156
- **Concern**: Relocated redaction section omits operational wait-ci/warn public-boundary warning. Scenario: Plan sub-bullets 1-5 and Edge cases "copy verbatim" do not carry the existing sentence that wait-ci/warn breadcrumb text can still reach committed logs after secrets-family redaction (CI failure strings, check names)
- **Proposed resolution**: Add a sixth sub-bullet or fold into sub-bullet 5: operational breadcrumb categories (wait-ci, warn) remain public-boundary content after pattern redaction

### FINDING_11:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:24-26
- **Concern**: The docs/run-logs.md subsection plan omits the feature's explicit path-resolution and basename-mapping acceptance details. Scenario: The feature description requires documenting the commit contract's path resolution, filter pattern, basename mapping, and partial-success semantics; the plan covers publisher/filter/fail-closed semantics but does not tell the implementer to document how the breadcrumb source directory is resolved or that accepted depth-1 *.ndjson files are published under the same basename into larch-logs/<skill>/<run-id>/breadcrumbs/
- **Proposed resolution**: Add explicit instructions for the new docs/run-logs.md subsection to document larch_log_breadcrumb_source_dir resolution (LARCH_BREADCRUMB_SOURCE_DIR override or log-root parent breadcrumbs fallback, with session-tmpdir containment) and same-basename depth-1 publication for accepted *.ndjson files

### FINDING_12:
- **Reviewer(s)**: Cursor-dyn-semantic-accuracy
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:17
- **Concern**: Proposed sub-bullet 4 omits session-tmpdir fail-closed rejections that lib-larch-log.sh enforces before and during the file loop. Scenario: Readers infer only absolute-path/symlink/hardlink/basename/redactor failures abort publish; sources outside IMPLEMENT/DESIGN/REVIEW/RESEARCH tmpdirs (scripts/lib-larch-log.sh:376-378,399-402) also rm staging and return 1 per scripts/test-larch-log.sh:246-265,433-451
- **Proposed resolution**: Add session-tmpdir constraints to sub-bullet 4 (and run-logs.md subsection (c)): source_dir and each candidate file must resolve under an allowed session tmp root

### FINDING_13:
- **Reviewer(s)**: Codex-dyn-semantic-accuracy
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lib-larch-log.sh:391-420
- **Concern**: The plan overstates the symlink and bad-basename fail-closed triggers. Scenario: Proposed docs say any symlink or bad basename in the breadcrumb source removes the whole directory, but the helper skips paths that fail -e before checking -L, so dangling symlinks are ignored, and it only validates bad basenames after the *.ndjson allowlist. A directory with good.ndjson plus a dangling symlink can still publish good.ndjson.
- **Proposed resolution**: Revise the prose to say existing matched symlink entries are rejected, regular hardlinked entries are rejected, invalid basenames are rejected for candidate *.ndjson files, and other ignored entries are not committed; or expand the plan to change code and tests to enforce the broader claim.
