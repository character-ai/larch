### OOS_1: [OUT_OF_SCOPE] Writer-parity lint is Makefile-only while lint-bg-wait-coverage also runs in pre-commit
- **Description**: [OUT_OF_SCOPE] Writer-parity lint is Makefile-only while lint-bg-wait-coverage also runs in pre-commit. Scenario: Contributors who rely on pre-commit but skip make lint could land a new marker writer without CLONE_PATH until CI
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: .pre-commit-config.yaml:667-672
- **Phase**: design



### OOS_2: Minimum-change alternative is delete dead marker block instead of parity-stamping it
- **Description**: Minimum-change alternative is delete dead marker block instead of parity-stamping it. Scenario: Keeping SITE=step3 marker logic plus new CLONE_PATH read preserves ~15 lines of code no production caller executes; lint inventory inclusion then forces perpetual maintenance on dead surface.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: skills/implement/scripts/run-step-checks.sh:60-74
- **Phase**: design



### OOS_3: Writer-parity lint is Makefile-only while sibling lint-bg-wait-coverage also runs in pre-commit
- **Description**: Writer-parity lint is Makefile-only while sibling lint-bg-wait-coverage also runs in pre-commit. Scenario: Contributors who rely on pre-commit but skip make lint can add a new bg-wait writer without CLONE_PATH until CI.
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: risk-integration
- **Location**: .pre-commit-config.yaml:667-672
- **Phase**: design



### OOS_4: [OUT_OF_SCOPE] New lint is wired only into make lint; sibling lint-bg-wait-coverage also has a pre-commit hook.
- **Description**: [OUT_OF_SCOPE] New lint is wired only into make lint; sibling lint-bg-wait-coverage also has a pre-commit hook.. Scenario: Local make lint catches drift; omitting pre-commit only affects contributors who skip make lint before commit. Optionally mirror lint-bg-wait-coverage with a pre-commit entry for lint bg-wait-writer-parity if hook parity is desired later. schema_version
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: .pre-commit-config.yaml:667-669
- **Phase**: design



### OOS_5: [OUT_OF_SCOPE] New lint is wired only into make lint; sibling lint-bg-wait-coverage also has a pre-commit hook.
- **Description**: [OUT_OF_SCOPE] New lint is wired only into make lint; sibling lint-bg-wait-coverage also has a pre-commit hook.. Scenario: Drift is still caught by make lint and CI harness targets; omitting pre-commit only affects contributors who skip make lint before commit.
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: .pre-commit-config.yaml:667-669
- **Phase**: design



### OOS_6: [OUT_OF_SCOPE] Inventory-only lint cannot catch a brand-new writer file until the list is updated
- **Description**: [OUT_OF_SCOPE] Inventory-only lint cannot catch a brand-new writer file until the list is updated. Scenario: Edge case 5 and failure mode 2 acknowledge inventory maintenance, but a new writer added outside the frozen list will not fail CI until someone extends the inventory. Acceptable tradeoff for minimum-change static lint; optional future enhancement is cross-check against lint_bg_wait_coverage KNOWN_BACKGROUND_COMMANDS marker_step mappings. ## Findings ### 1. code-quality / correctness — [SCOPE-REDUCTION] Primary shell fix is dead-path churn The plan’s Approach item 1 and firm `### UPDATED: skills/implement/scripts/run-step-checks.sh` treat the shell Step 3 block as the active gap. Repo evidence shows the opposite. Live `/implement` Step 3 launches the composite, not the shell wrapper: "$HOME/.cache/larch/sessions/implement-run-$PPID.sh" python/cli.py implement checks-commit-route --checks-site step3 --commit-site step4 --rebase-checkpoint-4r --forked-target "${forked_target:-false}" That composite already writes `implement-step3-checks` with `CLONE_PATH` from keepalive: def _write_bg_wait_marker(*, tmpdir: Path, step: str, timeout_s: int) -> None: ... f"CLONE_PATH={_read_keepalive_clone_path(tmpdir)}\n" ) with contextlib.suppress(OSError): (tmpdir / ".bg-wait-active").write_text(text, encoding="utf-8") marker = _checks_commit_route_marker(args.checks_site) with _optional_bg_wait_marker(tmpdir=implement_tmpdir, marker=marker): return _checks_commit_route_main_impl(args, implement_tmpdir) The shell path is explicitly legacy: ## Caller `skills/implement/SKILL.md` no longer invokes this wrapper for active Step 3. Keep it available for offline harnesses and any legacy helper-only paths until all callers are removed. The orphaned shell block still omits `CLONE_PATH`: printf 'PID=%s\nCLAUDE_PID=%s\nSTART_EPOCH=%s\nSTEP=implement-step3-checks\nTIMEOUT_S=10800\n' \ "$$" "$_step3_claude_pid" "$_step3_start" >"$IMPLEMENT_TMPDIR/.bg-wait-active" 2>/dev/null || true **Suggested revision:** Make the writer-parity lint the required deliverable; treat `run-step-checks.sh` as optional legacy parity or drop it from firm scope. If kept, document that `dispatch_commit_route.py` is the live Step 3 writer. ### 2. architecture — Lint needs write-site coupling, not file-level `CLONE_PATH=` The planned lint correctly avoids repo-wide grep and hook false positives by using a frozen writer inventory (Approach item 3; failure mode 1). Including `python/larch/implement/dispatch_commit_route.py` does protect the live Step 3/5-resume paths. The NEW module spec is underspecified on *where* `CLONE_PATH=` must appear. Sibling writers bind it to the marker body: _step5_clone_path="" if [ -f "$IMPLEMENT_TMPDIR/.larch-keepalive" ] && [ ! -L "$IMPLEMENT_TMPDIR/.larch-keepalive" ]; then _step5_clone_path=$(awk -F= '$1 == "CLONE_PATH" { sub(/^[^=]*=/, ""); print; exit }' "$IMPLEMENT_TMPDIR/.larch-keepalive" 2>/dev/null || true) fi printf 'PID=%s\nCLAUDE_PID=%s\nSTART_EPOCH=%s\nSTEP=implement-step5-review\nTIMEOUT_S=21600\nCLONE_PATH=%s\n' \ "$$" "$_step5_claude_pid" "$_step5_start" "$_step5_clone_path" >"$IMPLEMENT_TMPDIR/.bg-wait-active" 2>/dev/null || true **Suggested revision:** In `lint_bg_wait_writer_parity.py`, match the writer-evidence region (function/block containing `.bg-wait-active` write) and require `CLONE_PATH` in that same region’s emitted marker template. ### 3. What the plan gets right - **Fail-open parity:** Preserving `|| true` on the shell `printf` matches `step-5-review.sh:79` and keeps marker failures non-aborting. - **Keepalive semantics:** Planned `-f` + `! -L` + awk read matches siblings (`step-5-review.sh:75-76`). - **Hook consumer isolation:** Explicit inventory (not scanning `scripts/hook-bg-poll-guard.sh:103-124` or test harnesses) matches the stated failure mode. - **Inventory coverage:** Nine listed writers align with actual marker authors; `design_core.py` correctly covers delegated design Step 5c/final-summary paths (`design_core.py:172-188`). - **CI wiring:** Makefile pattern mirrors existing `lint-bg-wait-coverage` (`Makefile:37,186`). ### [OUT_OF_SCOPE] New writers outside the inventory stay undetected until manual list update Static inventory lint cannot discover writers added outside the frozen list. The plan acknowledges this (edge case 5). Acceptable for minimum-change scope; a future enhancement could diff against `lint_bg_wait_coverage.py` `KNOWN_BACKGROUND_COMMANDS` (`python/larch/lint/lint_bg_wait_coverage.py:41-101`).
- **Reviewer**: Cursor-dyn-Bg Wait Marker Integrity
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/lint/lint_bg_wait_writer_parity.py (planned)
- **Phase**: design



