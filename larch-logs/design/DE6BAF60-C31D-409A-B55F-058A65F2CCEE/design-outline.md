## Proposed Design Outline

### Goals
- Close the genuinely missing Codex-auth test gaps from issue #3476 across 4 harnesses (audit-first; skip already-covered items).
- Pin strip semantics (post-table selector, multiline state), probe hygiene (CODEX_HOME cleanup, trust argv, stamp isolation, sentinel leaks), and dispatch failure breadcrumbs.

### Non-goals
- No production-code changes; tests and harness fixtures only.
- No re-adding coverage that already exists (e.g. strip-failure fail-closed at test-lib-external-launcher-common.sh:168-187).
- No new test files, no Makefile/CI wiring changes.

### Approach sketch
- `scripts/test-lib-external-launcher-common.sh`: fix the trivially-passing post-table needle (line 162); add nested-selector strip + multiline-retention count assertions; add 2-3 multiline-state corruption fixtures.
- `scripts/test-check-reviewers.sh`: add temp `CODEX_HOME` cleanup assertions on 4 exit paths; trusted-project `-c` argv assertion; sentinel-absent sweep (`grep -r` over scratch TMPDIR); legacy env_key strip via stub-captured temp config; stamp write-side isolation assertions.
- `skills/review-and-fix/scripts/test-review-and-fix.sh` (dispatch section): auth-prep failure → `codex-auth-setup:` breadcrumb + cursor fallback; login fallback with fixture HOME auth.json symlink; env-key dispatch failure → `codex-env-key-failure:` breadcrumb in wrapper log + sidecar; widen sentinel-absent checks.
- `skills/implement/scripts/test-codex-implementer.sh`: env-key-mode auth-prep failure breadcrumb variant; temp-home (`/tmp/larch-codex-home-*`) cleanup assertions on success + auth-prep-failure paths.

### Surfaces in scope
- scripts/test-lib-external-launcher-common.sh
- scripts/test-check-reviewers.sh
- skills/review-and-fix/scripts/test-review-and-fix.sh
- skills/implement/scripts/test-codex-implementer.sh

### Open questions
- None.
