# emit-design-plan-preview.sh

**Purpose**: Emit the Step 3 plan-candidate preview or Gate C final-plan preview, with a shared large-plan summary note when `plan.txt` exceeds a size threshold. Called by `/design` Step 3 and Step 4b (Gate C).

**CLI**: `--design-tmpdir DIR --variant step3|gatec`. Reads `$design_tmpdir/plan.txt`.

**Allowlist validation**: Sources `scripts/lib-design-tmpdir.sh` and calls `larch_design_tmpdir_validate "$design_tmpdir"` inside each variant branch, after the existing `-z / ! -d / ! -s plan.txt` warning-and-exit-0 checks and before reading `plan.txt`. Validator failure routes to the variant's existing warning-and-exit-0 path (`**⚠ 3:**` or `**⚠ 4b:**`) so Step 3 / Gate C callers see a friendly diagnostic instead of a hard exit.

**Graceful-degrade contract**: All failure paths (missing tmpdir, missing plan, disallowed tmpdir) print a warning and exit 0. Step 3 and Gate C invoke this helper for display; they expect exit 0 even when `DESIGN_TMPDIR` is missing or invalid.

**Primary caller**: `/design` SKILL.md Step 3 and Step 4b (Gate C).

**Harness**: `skills/design/scripts/test-emit-design-plan-preview.sh`.
