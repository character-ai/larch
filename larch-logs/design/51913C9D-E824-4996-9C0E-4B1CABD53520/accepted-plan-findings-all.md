### FINDING_1: Unfiltered default history is undefined
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: important
- **Concern**: The command does not define what happens when neither `--window` nor `--since-tag` is supplied, so implementations may choose different history windows or truncate silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Pin CLI behavior: when neither `--window` nor `--since-tag` is set, load every commit that touched `BASELINE_RELPATH` oldest-to-newest; document that default in the CLI section and `docs/run-log-cli.md`; add one fixture test for unfiltered output.
  - From Cursor-Requirements: Specify default semantics explicitly: with no filter flags, load all commits touching BASELINE_RELPATH oldest-to-newest; detailed mode emits per-commit rows, summary mode aggregates across that full set. Add one fixture test for the no-flag path.


### FINDING_2: Since-tag needs peeled rev-range validation
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: important
- **Concern**: Tag-based filtering needs a precise peeled-commit rev range and ancestry check so `--since-tag` selects the intended post-tag commits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Specify that tag mode calls `log_path_commits(..., rev_range=f"{tag}..HEAD", ...)` after `rev-parse tag^{commit}`; fail exit 2 when the tag is missing or not an ancestor of HEAD; test malformed/missing tags.
  - From Cursor-Pragmatic: After `rev-parse` validates `TAG^{commit}`, pass `rev_range` as f"{peeled}..HEAD" (or equivalent) into `log_path_commits`; add a test that an annotated tag resolves to the same commit set as the peel step.


### FINDING_3: `--root` repo-root contract is missing
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements, Cursor-dyn-History Ledger Correctness
- **Severity**: important
- **Concern**: The `--root` contract is advertised but not pinned to a repo-root default or explicit git `cwd`, so history reads can point at the wrong tree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Reuse `lint_skill_closure_growth._coerce_root` and the same default `--root` as `skill-closure report`; pass `cwd=root` into all git helpers; exit 2 when `root` is not inside a git work tree; document the contract beside the command examples.
  - From Cursor-Innovation: Mirror `report_main`: add `--root` (default `Path(__file__).resolve().parents[3]`), validate with the same `_coerce_root` pattern, and pass the resolved root as `cwd` for all git reads.
  - From Cursor-Requirements: Document `--root` defaulting to the plugin repo root (same rule as `skill-closure report`), validate with `_coerce_root`, and pass that path as `cwd` to `log_path_commits` / `show_file`.
  - From Cursor-dyn-History Ledger Correctness: Mirror report_main: add `--root` with the same default and `_coerce_root` (or equivalent) and pass resolved root as cwd to log_path_commits and show_file.


### FINDING_4: Summary and first-seen baseline handling is underspecified
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation, Cursor-dyn-History Ledger Correctness, Codex-dyn-History Ledger Correctness
- **Severity**: important
- **Concern**: Summary mode needs explicit predecessor-snapshot and first-seen seeding rules so brand-new targets and the first post-filter delta are not lost.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: A fixture with a pre-tag commit, a tagged baseline revision, and post-tag changes should assert the first post-tag row has the correct `previous` and `delta` (same contract as the window test).
  - From Codex-Innovation: Seed summary rows from first snapshots as zero-delta entries, or compute start and end from the first and last snapshot per target.
  - From Cursor-dyn-History Ledger Correctness: Summary mode lists start, end, net delta, and aggregate by target, but does not say start is the pre-first-selected snapshot (including the out-of-window predecessor) and end is the snapshot after last selected. An implementer could sum detailed deltas only and mishandle first-seen rows or panel-tier window endpoints.
  - From Codex-dyn-History Ledger Correctness: Make summary aggregation walk the selected revision sequence, not just non-empty deltas, and seed first-seen targets with start=end=current and delta=0.


### FINDING_8: Fixture history should cover the design trajectory
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The fixture history should exercise the design-side trajectory, not only the panel-tier path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add a design-target history slice and expected delta assertions in the same temp-repo fixture, not just the panel-tier endpoint.


### FINDING_2: Since-tag fixture expectation must match the predecessor rule
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation, Codex-Requirements
- **Severity**: important
- **Concern**: The since-tag test fixture currently encodes the wrong predecessor for the first post-tag delta, so the test either needs to pin the tag to a non-touching commit or update the expected delta to the tagged commit’s baseline value, depending on the intended history shape.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: In the test section, require a trio where the tag annotates a commit that does not modify python/skill-closure-baseline.json (for example an docs-only commit between pre-tag and post-tag baseline bumps). State that expectation explicitly beside the pre-tag/tagged/post-tag fixture note.
  - From Codex-Innovation: Revise the bullet to assert the first post-tag delta against the tagged commit's baseline value, and name the fixture commits clearly as before_tag, at_tag, and after_tag.
  - From Codex-Requirements: Revise the fixture note so `--since-tag TAG` asserts the first selected commit against the nearest earlier touching revision in full history. For a pre-tag/tagged/post-tag trio with the tag on the middle commit, expect post-tag minus tagged.


### FINDING_1: `--since-tag` tag validation ignores resolved `--root`
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: `--since-tag` ref validation can run against the ambient checkout instead of the resolved `--root`, so the tag check and the history walk can disagree and produce empty or wrong post-tag summaries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: In the Tag filtering section, require tag rev-parse --verify (and any follow-on git calls) through the same ProcRunner/git._run path with cwd=resolved root, matching log_path_commits and show_file.


