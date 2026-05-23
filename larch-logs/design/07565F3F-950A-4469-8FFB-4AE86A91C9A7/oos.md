### OOS_1: Tighten count_filed_urls_union_files regex to recognize only `Filed URL:` lines
- **Description**: The current shared helper at `scripts/oos-disposition-shared.inc.bash` greps any `https://github.com/.../issues/[0-9]+` URL anywhere in the input file. After this change, `oos-accepted-design.md` is passed as a `--filed-urls-file` to the disposition gate, but the file ALSO contains OOS Descriptions written by reviewers, which may include "see also #1234" URLs. The gate could over-count and pass even when not all accepted OOS were actually filed. Affected file: `scripts/oos-disposition-shared.inc.bash`; potentially a new `count_filed_url_field_lines` helper that requires the `- **Filed URL**:` prefix on the same line.
- **Reviewer**: Claude (quick mode)
- **Vote tally**: N/A — quick-mode self-review
- **Phase**: design

### OOS_2: Cross-session sentinel persistence for /design re-invocations
- **Description**: The in-session sentinel `$DESIGN_TMPDIR/oos-issues-created.md` protects against double-filing within ONE /design invocation but does not survive across sessions (each /design run creates a fresh DESIGN_TMPDIR). Two /design runs on the same issue across sessions rely on /larch:issue's LLM dedup as the only backstop. A stable per-issue cache (e.g., `~/.cache/larch/design-oos-filed/<ISSUE_NUMBER>.md`) would provide deterministic cross-session protection. Affected files: `skills/design/scripts/file-design-oos.sh` (sentinel write path), `skills/design/SKILL.md` (Step 5b recovery path).
- **Reviewer**: Claude (quick mode)
- **Vote tally**: N/A — quick-mode self-review
- **Phase**: design
