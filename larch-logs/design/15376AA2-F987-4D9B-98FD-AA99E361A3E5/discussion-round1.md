## Decision 1: Lane scope — which default-mode codex lanes to fix
- **Question**: Fix all 3 broken default-mode codex lanes (launch-codex-implement.sh, lint-fix-loop.sh run_codex, review-and-fix.sh codex coder), or only the 2 named in the issue title (implement + lint-fix)?
- **Resolution**: All 3 lanes. Identical bug shape; one-line argv addition per lane; avoids an immediate OOS follow-up for review-and-fix.sh.
- **Source**: user

## Decision 2: Severity / consumer wiring — latent vs user-visible
- **Question**: Do the 3 broken lanes read the `.stderr-tail` artifact today (so a wrong source would be user-visible), or is this latent?
- **Resolution**: Latent. The only `.stderr-tail` readers are the collector path (compose-collector-failure-log.sh, resolve_collector_stderr_tail_file) and launch-claude-review.sh. The 3 broken lanes surface the raw SIDECAR_LOG / wrapper-log directly (or emit a generic failure line). Scope = correct the shared source-selection so `.stderr-tail` is right for every lane that passes through run-external-agent.sh. Do NOT add new consumer wiring (e.g. making step2-implement.sh read `.stderr-tail`) — out of scope for this issue.
- **Source**: codebase

## Decision 3: Cursor / capture-mode lanes — out of scope
- **Question**: Do the cursor lanes or capture-stdout(-only) lanes need the same fix?
- **Resolution**: No. --capture-stdout routes child stdout+stderr to OUTPUT; --capture-stdout-only routes child stderr to .diag — both already selected correctly. Intentional asymmetry (external-tool-launcher-parity.md): only default-mode codex lanes whose inherited fd2 lands in a custom sink are affected.
- **Source**: codebase

## Constraint 1: Must not break sink consumers; must stay backward-compatible
- **Question**: What must not break?
- **Resolution**: The child's stderr must keep flowing to the custom sink via inherited fd2 (external_is_auth_failure greps SIDECAR_LOG for auth errors) — the wrapper must NOT redirect child stderr to ${output}.sidecar itself. The new --stderr-sink option is optional; lanes that omit it (launch-codex-ci.sh, launch-review.sh, all capture-mode lanes) must behave byte-identically to today.
- **Source**: codebase
