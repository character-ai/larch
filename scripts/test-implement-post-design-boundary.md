`scripts/test-implement-post-design-boundary.sh` is a structural regression test for issue #1014: it pins the post-/design boundary checkpoint reminder in `skills/implement/SKILL.md` Step 1 (normal mode) and the matching `--emit-load-breadcrumb` flag handler in `skills/design/scripts/read-design-manifest.sh`.

Assertions:
- (A) `Post-/design boundary checkpoint` blockquote present in SKILL.md.
- (B) Anti-pattern strings `returning control`, `design phase complete`, `handing off` present in SKILL.md (case-insensitive). These are the literal phrases the reminder warns against; their presence in the warning text is the load-bearing signal.
- (C) Both breadcrumb literals present in SKILL.md: `🔃 1.r: design plan | rebase` and `🔶 2: implementation`.
- (D) `NEVER #7` reference present in SKILL.md.
- (E) Manifest-loaded breadcrumb literal `📥 1: design plan — manifest loaded` present in SKILL.md.
- (F) The post-/design re-run of `read-design-manifest.sh` in SKILL.md forwards `--emit-load-breadcrumb`.
- (G) `read-design-manifest.sh` defines the `--emit-load-breadcrumb` flag handler.
- (H) `read-design-manifest.sh` emits the breadcrumb literal on the success path.

Edit-in-sync rule: any change to the reminder phrasing must preserve the four anchor strings (`returning control`, `design phase complete`, `handing off`, `NEVER #7`), the two breadcrumbs, the `Post-/design boundary checkpoint` header, and the `--emit-load-breadcrumb` forwarding. Changing any of these silently weakens the reminder's value — the test fails to flag the regression.

Wired into `make lint` via the `test-implement-post-design-boundary` target. Mirrors `scripts/test-implement-rebase-macro.sh` and `skills/fix-issue/scripts/test-fix-issue-bail-detection.sh`.
