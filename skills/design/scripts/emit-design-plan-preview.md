# emit-design-plan-preview.sh

**Purpose**: Emit the Step 3 plan-candidate preview or Gate C final-plan preview, with a shared large-plan summary note when `plan.txt` exceeds a size threshold.

**CLI**: `--design-tmpdir DIR --variant step3|gatec`. Reads `$design_tmpdir/plan.txt`.

**Allowlist validation**: Sources `scripts/lib-design-tmpdir.sh` and calls `larch_design_tmpdir_validate "$design_tmpdir"` inside each variant branch, after the existing `-z / ! -d / ! -s plan.txt` warning-and-exit-0 checks and before reading `plan.txt`. Validator failure routes to the variant's existing warning-and-exit-0 path (`**⚠ 3:**` or `**⚠ 4b:**`) so Step 3 / Gate C callers see a friendly diagnostic instead of a hard exit.

**Graceful-degrade contract**: All failure paths (missing tmpdir, missing plan, disallowed tmpdir) print a warning and exit 0. Callers expect exit 0 even when `DESIGN_TMPDIR` is missing or invalid.

**`step3` variant — pure renderer**: The `step3` case is a pure renderer. It does NOT read or write `.step3-entry-plan-printed`. Sentinel ownership belongs to `run-step3-review.sh --preview-only`, which calls this script via the `RUN_STEP3_EMIT_PREVIEW_SH` override seam and applies allowlist-gated sentinel touch rules after inspecting the renderer output.

**Primary callers**:
- `step3` variant: `run-step3-review.sh --preview-only` (driver-owned sentinel, allowlist-gated touch).
- `gatec` variant: `/design` SKILL.md Step 4b (Gate C approval gates).

**Harness**: `skills/design/scripts/test-emit-design-plan-preview.sh`.
