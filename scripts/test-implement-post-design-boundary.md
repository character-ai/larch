`scripts/test-implement-post-design-boundary.sh` is a structural regression test for issue #1014: it pins the post-/design boundary checkpoint reminder in `skills/implement/SKILL.md` Step 1 (normal mode) and the matching `--emit-load-breadcrumb` flag handler in `skills/design/scripts/read-design-manifest.sh`.

Assertions:
- (A) `Post-/design boundary checkpoint` header present in SKILL.md, and the awk-extracted slice (header line through the next blank line) is non-empty.
- (B) Anti-pattern strings `returning control`, `design phase complete`, `handing off` present **inside the boundary-checkpoint slice** from (A) (case-insensitive). These literal phrases are load-bearing — they are the exact patterns the reminder warns against; drifting them out of the warning text silently weakens the reminder, so the assertion is scoped to the slice rather than file-wide.
- (C) Both breadcrumb literals present in SKILL.md: `🔃 1.r: design plan | rebase` and `🔶 2: implementation`.
- (D) `NEVER #7` reference present in SKILL.md.
- (E) Manifest-loaded breadcrumb literal `📥 1: design plan — manifest loaded (plan=` present in SKILL.md.
- (F) The post-/design re-run of `read-design-manifest.sh` in SKILL.md forwards `--emit-load-breadcrumb`.
- (G) `read-design-manifest.sh` defines the `--emit-load-breadcrumb` flag handler.
- (H) `read-design-manifest.sh` emits the breadcrumb literal on the success path with the `plan=<basename>` form (not `PLAN_FILE=<basename>`).
- (I) Neither `read-design-manifest.sh` nor SKILL.md retains the legacy `PLAN_FILE=<basename>` breadcrumb form (guards against partial revert; the legacy form would collide at the KV-namespace level with the canonical-path envelope key emitted by `check_path`, per #1014 review FINDING_2).
- (J) **Stdout-shape integration test**: synthesizes a minimal valid manifest under `mktemp`, runs the reader with `--emit-load-breadcrumb`, and asserts (a) `MANIFEST_OK=true` is emitted, (b) the breadcrumb is the LAST line of stdout, and (c) on a missing-manifest failure path the reader emits `MANIFEST_FAILED=true` and SUPPRESSES the breadcrumb. This catches regressions that static `grep`s alone (G/H) cannot — for example, a future edit that emits the breadcrumb before `MANIFEST_OK=true`, drops emission entirely, or fires it on the failure path.

Edit-in-sync rule: any change to the reminder phrasing must preserve the four anchor strings (`returning control`, `design phase complete`, `handing off`, `NEVER #7`), the two breadcrumbs, the `Post-/design boundary checkpoint` header, the `--emit-load-breadcrumb` forwarding, and the `plan=<basename>` breadcrumb form (NOT the legacy `PLAN_FILE=<basename>` form). Changing any of these silently weakens the reminder's value — the test fails to flag the regression.

Wired into `make lint` via the `test-implement-post-design-boundary` target. Mirrors `scripts/test-implement-rebase-macro.sh` and `skills/fix-issue/scripts/test-fix-issue-bail-detection.sh`.
